"""Local Java/MySQL navigation acceptance; only uniquely named fixtures are mutated.

Uses existing local verification login helpers, never a user's browser/chat token.
"""
import importlib.util
import json
import math
import pathlib
import time
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nav_helpers', ROOT / 'scripts/verify-logistics-list.py')
listing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listing)
helpers = listing.helpers
api, mysql, quote = helpers.api, helpers.mysql, helpers.sql_value
BASE = 'http://127.0.0.1:5173/java-api'
PREFIX = 'nav_' + uuid.uuid4().hex[:10]
report = {'passed': False, 'mode': 'real local Java + MySQL 3307; unique simulation fixtures', 'checks': []}


def check(name, condition):
    assert condition, name
    report['checks'].append(name)
    print('PASS API: ' + name, flush=True)


def distance(a, b):
    lat1, lat2 = math.radians(a['latitude']), math.radians(b['latitude'])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b['longitude']-a['longitude'])/2)**2
    return 6371000*2*math.asin(math.sqrt(min(1,max(0,h))))


def main():
    admin = None
    stations, aircraft, orders, tasks, users, tokens = [], [], [], [], [], []

    def req(path, body=None, method=None, token=None):
        _, result = api(BASE, path, method or ('POST' if body is not None else 'GET'), body, token or admin)
        assert result.get('code') == 200, (path, result.get('code'), result.get('msg'))
        return result.get('data')

    def task_snapshot(task_id, token=None):
        return next(t for t in req('/sky/snapshot', token=token)['tasks'] if t['id'] == task_id)

    def order(suffix):
        order_id = req('/sky/logistics/orders', {'cargoName': PREFIX+'_'+suffix, 'weight': 1,
            'startStationId': stations[0], 'endStationId': stations[1], 'deadlineMinutes': 30, 'reason': PREFIX})
        orders.append(order_id)
        task_id = req('/sky/logistics/orders/'+order_id)['taskId']
        tasks.append(task_id)
        return task_id

    def action(task_id, name):
        req('/sky/tasks/'+task_id+'/'+name, {'reason': PREFIX, **({'aircraftId': aircraft[0]} if name == 'assign' else {})})

    try:
        check('dedicated MySQL 3307 only', mysql('SELECT @@port;') == '3307')
        _, denied = api(BASE, '/sky/snapshot')
        check('anonymous snapshot denied', denied.get('code') == 401)
        admin = helpers.login(BASE)
        tokens.append(admin)
        for index in range(2):
            stations.append(req('/sky/stations', {'name': PREFIX+'_station_'+str(index), 'type':'logistics',
                'longitude':120.31+index*.003, 'latitude':30.32, 'status':'enabled'}))
        aircraft.append(req('/sky/aircraft', {'name':PREFIX+'_cargo', 'type':'cargo', 'model':'navigation-verification',
            'longitude':120.31, 'latitude':30.32, 'battery':100, 'payloadCapacity':20, 'seats':0}))
        task_id = order('complete')
        req('/sky/tasks/'+task_id+'/route', {'expectedRevision':1, 'waypoints':[
            {'longitude':120.31,'latitude':30.325}, {'longitude':120.313,'latitude':30.325}], 'reason':PREFIX}, 'PUT')
        before = task_snapshot(task_id)
        check('snapshot navigation starts at frozen v2 origin', before['routeRevision'] == 2 and before['navigation']['position']['offsetSeconds'] == 0)
        check('detour remaining mileage exceeds destination straight distance', before['navigation']['remainingRouteMeters'] > before['navigation']['destinationDistanceMeters'] * 4)
        check('initial remaining matches full saved route distance', abs(before['navigation']['remainingRouteMeters']-before['routeDistanceMeters']) < 1e-6)
        before_get = mysql('SELECT COUNT(*) FROM st_audit;')
        task_snapshot(task_id)
        req('/sky/tasks/'+task_id+'/tracks')
        check('navigation and tracks GET do not create business audit', mysql('SELECT COUNT(*) FROM st_audit;') == before_get)

        _, roles = api(BASE, '/system/role/list?pageNum=1&pageSize=100', token=admin)
        role = next(r['roleId'] for r in roles['rows'] if r['roleKey'] == 'sky_viewer')
        name, password = PREFIX+'v', uuid.uuid4().hex[:12]+'Az!3'
        req('/system/user', {'userName':name,'nickName':name,'password':password,'deptId':100,
            'status':'0','sex':'0','roleIds':[role],'postIds':[]})
        _, found = api(BASE, '/system/user/list?userName='+name, token=admin)
        users.append(next(u['userId'] for u in found['rows'] if u['userName'] == name))
        viewer = listing.login_as(BASE, name, password)
        tokens.append(viewer)
        check('read-only viewer receives navigation without dispatch permission', task_snapshot(task_id, viewer)['navigation'] == before['navigation'])
        action(task_id, 'assign')
        action(task_id, 'start')
        samples = []
        deadline = time.monotonic()+50
        while time.monotonic() < deadline:
            value = task_snapshot(task_id)
            nav, points = value['navigation'], value['routePoints']
            p = nav['position']
            future = [point for point in points if point['offsetSeconds'] > p['offsetSeconds']]
            expected = sum(distance(a,b) for a,b in zip([p]+future, future))
            assert abs(nav['remainingRouteMeters']-expected) < 1e-5
            assert abs(nav['destinationDistanceMeters']-distance(p,points[-1])) < 1e-5
            samples.append((value['elapsedSeconds'],nav['remainingRouteMeters']))
            if value['status'] == 'completed': break
            time.sleep(1)
        check('executing simulation reaches server-confirmed completion', value['status'] == 'completed')
        check('distance decreases along actual waypoint legs', len(samples)>3 and all(b[1]<=a[1]+1e-6 for a,b in zip(samples,samples[1:])) and samples[0][1]>samples[-1][1])
        check('completed navigation is zero at landed destination', nav['remainingRouteMeters'] == 0 and nav['destinationDistanceMeters'] == 0 and p['altitude'] == 0)
        tracks = req('/sky/tasks/'+task_id+'/tracks', token=viewer)
        check('saved flown history exists and last point matches destination', len(tracks)>3 and distance(tracks[-1],p)<1e-6)
        check('flight completion does not auto-confirm logistics delivery', req('/sky/logistics/orders/'+orders[0])['status'] == 'created')
        # A second task reuses the aircraft. Old navigation must remain immutable.
        old_nav = nav
        second = order('cancel')
        action(second,'assign'); action(second,'start')
        time.sleep(3)
        action(second,'cancel')
        stopped = task_snapshot(second)
        time.sleep(2)
        check('cancelled task freezes its last route-time position', stopped['navigation'] == task_snapshot(second)['navigation'] and stopped['navigation']['remainingRouteMeters'] > 0)
        check('aircraft reuse cannot move the completed task marker', task_snapshot(task_id)['navigation'] == old_nav)
        request = urllib.request.Request(BASE+'/sky/stream', headers={'Authorization':'Bearer '+viewer,'Accept':'text/event-stream'})
        with urllib.request.urlopen(request, timeout=15) as stream:
            for line in stream:
                if line.startswith(b'data:'):
                    streamed = next(t for t in json.loads(line[5:])['tasks'] if t['id'] == second)
                    check('real SSE publishes matching server navigation', streamed['navigation'] == stopped['navigation'])
                    break
        report['samples'] = samples
        report['passed'] = True
    finally:
        def ids(values): return ','.join(quote(v) for v in values) or "''"
        # Exact-prefix recovery covers a successful commit followed by an interrupted HTTP response.
        for row in mysql('SELECT id,task_id FROM st_logistics_order WHERE LEFT(cargo_name,'+str(len(PREFIX))+')='+quote(PREFIX)+';').splitlines():
            o,t = row.split('\t')
            if o not in orders: orders.append(o)
            if t not in tasks: tasks.append(t)
        entities = orders+tasks+aircraft+stations
        check_ids = mysql('SELECT id FROM st_airspace_check WHERE task_id IN ('+ids(tasks)+');').splitlines()
        mysql(f"""START TRANSACTION;
            SELECT tick FROM st_traffic_clock WHERE id=1 FOR UPDATE;
            SELECT id FROM st_task WHERE id IN ({ids(tasks)}) ORDER BY id FOR UPDATE;
            DELETE FROM st_audit WHERE entity_id IN ({ids(entities+check_ids)});
            DELETE FROM st_traffic_check WHERE task_id IN ({ids(tasks)});
            DELETE FROM st_airspace_check WHERE task_id IN ({ids(tasks)});
            DELETE FROM st_track WHERE task_id IN ({ids(tasks)});
            DELETE FROM st_report WHERE task_id IN ({ids(tasks)});
            DELETE FROM st_event WHERE task_id IN ({ids(tasks)});
            DELETE FROM st_logistics_order WHERE id IN ({ids(orders)});
            DELETE FROM st_task WHERE id IN ({ids(tasks)});
            DELETE FROM st_aircraft WHERE id IN ({ids(aircraft)});
            DELETE FROM st_station WHERE id IN ({ids(stations)});
            COMMIT;""")
        for user in users:
            if admin: req('/system/user/'+str(user), method='DELETE')
        for token in reversed(tokens): api(BASE,'/logout','POST',token=token)
        report['cleanup'] = {table:int(mysql(f'SELECT COUNT(*) FROM {table} WHERE {key} IN ({ids(values)});'))
            for table,key,values in [('st_task','id',tasks),('st_task_route','task_id',tasks),('st_track','task_id',tasks),
                ('st_logistics_order','id',orders),('st_aircraft','id',aircraft),('st_station','id',stations),('st_audit','entity_id',entities+check_ids)]}
        if any(report['cleanup'].values()): report['passed'] = False
        target = ROOT.parent/'docs/verification/navigation-api.json'
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Report: docs/verification/navigation-api.json',flush=True)
    assert report['passed']


if __name__ == '__main__': main()
