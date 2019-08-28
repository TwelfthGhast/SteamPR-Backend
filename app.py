from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
import psycopg2
import locale #comma formatting for numbers

cacheconfig = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "simple", # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 60*60*12
}

app = Flask(__name__)
app.config.from_mapping(cacheconfig)
cache = Cache(app)
app.config['JSON_SORT_KEYS'] = False
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

DB_USER = ""
DB_PASS = ""
DB_NAME = ""
MAX_ITERATION = 0
ACC_COUNT = 0
DB_PR_NAME = ""
DB_REL_NAME = ""
DB_BDG_NAME = ""

API_DOMAIN = "https://api.steampagerank.com/1.0/"

STATUS_BADREQUEST = 400

RANK_PERCENTILES = []

def calc_level(weighting):
    xp = int(weighting * 100)
    level = 0
    multiplier = 1
    while xp - (multiplier * 1000) >= 0:
        level += 10
        xp -= multiplier * 1000
        multiplier += 1
    while xp - (multiplier * 100) >= 0:
        level += 1
        xp -= multiplier * 100
    return level

@app.route('/')
@cache.memoize(timeout=60*60*24*7)
def main_page():
    return render_template('index.html', track_no=locale.format("%d", ACC_COUNT, grouping=True))

@app.route('/api/')
@cache.memoize(timeout=60*60*24*7)
def api_documentation():
    return render_template('api.html',apiv1=API_DOMAIN)

@app.route('/about/')
@cache.memoize(timeout=60*60*24*7)
def about_site():
    return render_template('about.html')

@app.route('/1.0/GetIteration/')
@cache.memoize(timeout=60*60*24*7)
def iteration_count():
    return jsonify(iteration=MAX_ITERATION)

@app.route('/1.0/GetBadge/')
def badge_api():
    badgeid = request.args.get("badgeid", 1)
    appid = request.args.get("appid", -1)
    limit = request.args.get("limit", 200)
    epoch = request.args.get("epoch", 0)
    minxp = request.args.get("xpmin", 0)
    maxxp = request.args.get("xpmax", 10000000000)
    foils = request.args.get("foil", -1)
    try:
        badgeid = int(badgeid)
        appid = int(appid)
        limit = int(limit)
        epoch = int(epoch)
        minxp = int(minxp)
        maxxp = int(maxxp)
        foils = int(foils)
        if limit > 1000:
            limit = 1000
        if badgeid != 1:
            appid = -1
        if foils < -1 or foils > 1:
            foils = -1
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        if foils != -1:
            cur.execute("SELECT steamid64, completed, xp, foil FROM " + DB_BDG_NAME + " WHERE badgeid = %s AND appid = %s AND completed > %s AND xp >= %s AND xp <= %s AND foil = '%s' ORDER BY completed LIMIT %s;",
                        (badgeid, appid, epoch, minxp, maxxp, foils, limit))
        else:
            cur.execute("SELECT steamid64, completed, xp, foil FROM " + DB_BDG_NAME + " WHERE badgeid = %s AND appid = %s AND completed > %s AND xp >= %s AND xp <= %s ORDER BY completed LIMIT %s;",
                        (badgeid, appid, epoch, minxp, maxxp, limit))
        row = cur.fetchall()
        data = []
        for i in row:
            if appid > 0 and badgeid == 1:
                data.append({
                    "steamid64" : i[0],
                    "completed" : i[1],
                    "xp"        : i[2],
                    "badgeid"   : badgeid,
                    "appid"     : appid,
                    "foil"      : i[3]
                })
            else:
                data.append({
                    "steamid64": i[0],
                    "completed": i[1],
                    "xp": i[2],
                    "badgeid": badgeid
                })
        return jsonify(response=data)
    except (Exception, psycopg2.DatabaseError)  as error:
        print(error)
        return jsonify(error="An error occurred. Please check your parameters and try again"), STATUS_BADREQUEST


@app.route('/1.0/GetProfile/')
def profile_api():
    steamid64 = request.args.get("steamid")
    try:
        steamid64 = int(steamid64)
        str_steamid64 = str(steamid64)
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        cur.execute("SELECT weighting, level FROM " + DB_PR_NAME + " WHERE steamid64 = %s AND iteration = %s;",
                    (str_steamid64, MAX_ITERATION))
        if cur.rowcount > 0:
            row = cur.fetchone()
            ret_weighting = row[0]
            ret_level = row[1]
            ret_replevel = calc_level(ret_weighting)
            # Descending order helps with showing a more meaningful level graph.
            cur.execute("SELECT badgeid, completed, xp, appid, foil FROM " + DB_BDG_NAME + " WHERE steamid64 = %s ORDER BY completed DESC;",
                        (str_steamid64, ))
            badges_list = []
            if cur.rowcount > 0:
                row = cur.fetchall()
                for i in row:
                    if i[3] >= 0:
                        badges_list.append({
                            'badgeid': i[0],
                            'completed': i[1],
                            'xp': i[2],
                            'appid': i[3],
                            'foil': i[4]
                        })
                    else:
                        badges_list.append({
                            'badgeid': i[0],
                            'completed': i[1],
                            'xp': i[2],
                            'foil': i[4]
                        })
            cur.execute("SELECT steamid64out, since FROM " + DB_REL_NAME + " WHERE steamid64in = %s ORDER BY since;", (str_steamid64,))
            friends_list = []
            if cur.rowcount > 0:
                row = cur.fetchall()
                for i in row:
                    friends_list.append({
                        'steamid64': i[0],
                        'since': i[1]
                    })
            else:
                cur.execute("SELECT steamid64in, since FROM " + DB_REL_NAME + " WHERE steamid64out = %s ORDER BY since;", (str_steamid64,))
                row = cur.fetchall()
                for i in row:
                    friends_list.append({
                        'steamid64': i[0],
                        'since': i[1]
                    })
            conn.close()
            return jsonify(steamid64 = str_steamid64,
                           weighting = ret_weighting,
                           level = ret_level,
                           reputation_level = ret_replevel,
                           badges=badges_list,
                           friends=friends_list)
        else:
            return jsonify(error="steamid64 not in database")
    except (Exception, psycopg2.DatabaseError)  as error:
        print(error)
        return jsonify(error="An error occurred. Please check your parameters and try again"), STATUS_BADREQUEST

@app.route('/1.0/GetList/')
def database_api():
    get_levelmin = request.args.get("lvlmin", 0)
    get_levelmax = request.args.get("lvlmax", 100000)
    get_weightmax = request.args.get("wgtmax", 100000000)
    get_weightmin = request.args.get("wgtmin", 0)
    get_num = request.args.get("limit", 200)
    try:
        # Format inputs (prevents errors and sql injections)
        get_levelmin = int(get_levelmin)
        get_levelmax = int(get_levelmax)
        get_weightmax = float(get_weightmax)
        get_weightmin = float(get_weightmin)
        get_num = int(get_num)
        if get_num > 1000:
            get_num = 1000
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        cur.execute("SELECT steamid64, level, weighting FROM " + DB_PR_NAME + " WHERE level >= %s AND level <= %s AND iteration = %s AND weighting >= %s AND weighting <= %s ORDER BY weighting DESC LIMIT %s;",
                (get_levelmin, get_levelmax, MAX_ITERATION, get_weightmin, get_weightmax, get_num))
        row = cur.fetchall()
        conn.close()
        data_list = []
        for i in row:
            data_item = {
                'steamid64' : i[0],
                'level'     : i[1],
                'weighting' : i[2]
            }
            data_list.append(data_item)
        return jsonify(response=data_list)
    except (Exception, psycopg2.DatabaseError)  as error:
        print(error)
        return 'An error occurred'

@app.route('/1.0/GetRank/<steamid64>')
@cache.memoize(timeout=60*60*24*7) #cache for a week
def get_rank(steamid64):
    try:
	    steamid64 = int(steamid64)
	    conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
	    cur = conn.cursor()
	    cur.execute("SELECT weighting, level FROM " + DB_PR_NAME + " WHERE steamid64 = '%s' AND iteration = %s;",
		        (steamid64, MAX_ITERATION))
	    row = cur.fetchone()
	    cur.execute("SELECT COUNT(*) FROM " + DB_PR_NAME + " WHERE level = %s AND iteration = %s;",
		        (row[1], MAX_ITERATION))
	    max = cur.fetchone()
	    # Inaccurate float comparisons means we have to add condition where steamid != what we are comparing.
	    cur.execute("SELECT COUNT(*) FROM " + DB_PR_NAME + " WHERE level = %s AND iteration = %s AND weighting > %s AND steamid64 != '%s';",
		        (row[1], MAX_ITERATION, row[0], steamid64))
	    rank = cur.fetchone()
	    conn.close()
	    percentile = 100
	    for i in RANK_PERCENTILES:
		if row[0] >= i['weighting']:
		    percentile = i['percentile']
		    break
	    return jsonify(playerlevel=row[1],
		           samelevel=max[0],
		           ranklevel=rank[0] + 1,
		           overallpercentile=percentile)
    except:
       return jsonify(error="An unexpected error occurred")


@app.errorhandler(404)
def not_found(error):
    return '404 Not found', 404

@app.before_first_request
def housekeeping():
    conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    cur.execute("SELECT iteration FROM " + DB_PR_NAME + " ORDER BY iteration DESC LIMIT 1;")
    row = cur.fetchone()
    global MAX_ITERATION
    MAX_ITERATION = int(row[0])
    cur.execute("SELECT COUNT(*) FROM " + DB_PR_NAME + " WHERE iteration = %s;", (MAX_ITERATION, ))
    row = cur.fetchone()
    global ACC_COUNT
    ACC_COUNT = int(row[0])
    for i in range(1, 101):
        lim = int(ACC_COUNT / 100 * i)
        cur.execute("SELECT weighting FROM " + DB_PR_NAME + " WHERE iteration = %s ORDER BY weighting DESC LIMIT 1 OFFSET %s;",
                    (MAX_ITERATION, lim))
        if cur.rowcount == 0:
            break
        row = cur.fetchone()
        RANK_PERCENTILES.append({
            "percentile" : i,
            "weighting" : row[0]
        })
    conn.close()

if __name__ == '__main__':
    app.run()
