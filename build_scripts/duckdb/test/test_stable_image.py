"""Real linux/amd64 release-image checks; run via build-stable-pg.sh --verify.

Requires disposable PostgreSQL and Quack/gateway services. No host dependencies.
"""
import concurrent.futures
import json
import os
import platform
import tempfile
import functools
import http.server
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import duckdb

URI = os.environ['QUACK_URI']
TOKEN = os.environ['QUACK_TOKEN']
URL = os.environ['GATEWAY_URL']


def request(path, body=None, token=TOKEN, status=200):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(URL + path, data=data, headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = json.load(response)
        assert response.status == status, (response.status, payload)
        return payload


def query(sql, **kwargs):
    return request('/query', {'sql': sql, **kwargs})


class StableImage(unittest.TestCase):
    def test_01_release_and_offline_extensions(self):
        self.assertEqual(platform.machine(), 'x86_64')
        self.assertEqual(duckdb.__version__, '2.0.0')
        with duckdb.connect() as c:
            self.assertEqual(c.sql('SELECT version()').fetchall()[0], ('v2.0.0',))
            c.execute('SET autoinstall_known_extensions=false')
            c.execute('SET autoload_known_extensions=false')
            for ext in ('postgres', 'quack', 'httpfs', 'json', 'parquet', 'icu'):
                c.execute(f'LOAD {ext}')
            self.assertEqual(c.sql('SELECT 6*7').fetchall()[0], (42,))

    def test_02_sql_files_and_transactions(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as c:
            c.execute('CREATE TABLE t AS SELECT i, i % 3 AS g FROM range(100) r(i)')
            c.execute('BEGIN')
            c.execute('DELETE FROM t WHERE i < 10')
            c.execute('ROLLBACK')
            self.assertEqual(c.sql('SELECT count(*), sum(i) FROM t').fetchall()[0], (100, 4950))
            self.assertEqual(c.sql('SELECT list_filter([1,2,3], lambda x: x > 1)').fetchall()[0], ([2,3],))
            self.assertEqual(c.sql("SELECT json_extract_string('{\"a\":\"中文\"}', '$.a')").fetchall()[0], ('中文',))
            for fmt in ('PARQUET', 'CSV', 'JSON'):
                path = str(Path(directory) / ('rows.' + fmt.lower()))
                c.execute(f"COPY t TO '{path}' (FORMAT {fmt})")
                reader = {'PARQUET':'read_parquet', 'CSV':'read_csv_auto', 'JSON':'read_json_auto'}[fmt]
                self.assertEqual(c.sql(f"SELECT count(*), sum(i) FROM {reader}('{path}')").fetchall()[0], (100,4950))
            self.assertEqual(c.sql("SELECT count(*) FROM t a JOIN t b USING (i)").fetchall()[0], (100,))
            self.assertEqual(c.sql("SELECT max(n) FROM (SELECT row_number() OVER (ORDER BY i) n FROM t)").fetchall()[0], (100,))
            c.execute('LOAD icu')
            self.assertEqual(c.sql("SELECT extract(hour FROM timezone('Asia/Shanghai', TIMESTAMPTZ '2026-10-23 00:00:00+00'))").fetchall()[0], (8,))

    def test_02b_httpfs_and_release_features(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as c:
            path = Path(directory) / 'remote.parquet'
            c.execute(f"COPY (SELECT 42 AS n) TO '{path}' (FORMAT PARQUET)")
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
            server = http.server.ThreadingHTTPServer(('0.0.0.0', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                c.execute('LOAD httpfs')
                self.assertEqual(c.sql(f"SELECT * FROM read_parquet('http://127.0.0.1:{server.server_port}/remote.parquet')").fetchall()[0], (42,))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
            c.execute('CREATE TABLE events(payload VARIANT)')
            c.execute("INSERT INTO events VALUES ('{\"id\":42}'::JSON::VARIANT)")
            self.assertEqual(c.sql('SELECT variant_type(payload) FROM events').fetchall()[0], ('OBJECT',))
            c.execute('CREATE TABLE target(id INTEGER, val INTEGER)')
            c.execute('CREATE TABLE audit(id INTEGER, old_val INTEGER, new_val INTEGER)')
            c.execute('INSERT INTO target VALUES (1,10)')
            c.execute("CREATE TRIGGER trg_audit AFTER UPDATE ON target REFERENCING OLD TABLE AS o NEW TABLE AS n FOR EACH STATEMENT INSERT INTO audit SELECT n.id,o.val,n.val FROM o JOIN n ON o.id=n.id")
            c.execute('UPDATE target SET val=20 WHERE id=1')
            self.assertEqual(c.sql('SELECT * FROM audit').fetchall(), [(1,10,20)])

    def test_03_postgres_crud_types_and_rollback(self):
        with duckdb.connect() as c:
            c.execute('LOAD postgres')
            dsn = os.environ['PG_DSN'].replace("'", "''")
            c.execute(f"ATTACH '{dsn}' AS pg (TYPE postgres)")
            c.execute('DROP TABLE IF EXISTS pg.public.stable_verify')
            c.execute('CREATE TABLE pg.public.stable_verify (id INTEGER, label VARCHAR, amount DECIMAL(18,2), day DATE, enabled BOOLEAN)')
            c.execute("INSERT INTO pg.public.stable_verify VALUES (1,'中文',12.34,DATE '2026-10-23',true),(2,NULL,NULL,NULL,false)")
            row = c.sql('SELECT label, amount::VARCHAR, day::VARCHAR, enabled FROM pg.public.stable_verify WHERE id=1').fetchall()[0]
            self.assertEqual(row, ('中文','12.34','2026-10-23',True))
            c.execute("UPDATE pg.public.stable_verify SET label='updated' WHERE id=1")
            c.execute('BEGIN')
            c.execute('DELETE FROM pg.public.stable_verify')
            c.execute('ROLLBACK')
            self.assertEqual(c.sql('SELECT count(*) FROM pg.public.stable_verify').fetchall()[0], (2,))
            c.execute('DELETE FROM pg.public.stable_verify WHERE id=2')
            self.assertEqual(c.sql('SELECT label FROM pg.public.stable_verify').fetchall()[0], ('updated',))
            self.assertEqual(c.sql('SELECT count(*) FROM pg.public.stable_verify p JOIN range(3) r(i) ON p.id=r.i').fetchall()[0], (1,))

    def test_04_quack_attach_query_and_auth(self):
        with duckdb.connect() as c:
            c.execute('LOAD quack')
            self.assertEqual(c.sql(f"SELECT * FROM quack_query('{URI}', 'SELECT 42', token => '{TOKEN}', disable_ssl => true)").fetchall()[0], (42,))
            c.execute(f"ATTACH '{URI}' AS remote (TYPE quack, TOKEN '{TOKEN}', DISABLE_SSL true)")
            c.execute('CREATE OR REPLACE TABLE remote.stable_persist AS SELECT i FROM range(100) r(i)')
            self.assertEqual(c.sql('SELECT count(*), sum(i) FROM remote.stable_persist').fetchall()[0], (100,4950))
            c.execute('DETACH remote')
            with self.assertRaises(duckdb.Error):
                c.sql(f"SELECT * FROM quack_query('{URI}', 'SELECT 42', token => 'wrong', disable_ssl => true)").fetchall()

    def test_05_gateway_health_auth_formats_limits_errors(self):
        self.assertEqual(request('/health')['upstream'], 'ok')
        request('/query', {'sql':'SELECT 1'}, token='wrong', status=401)
        self.assertEqual(query("SELECT 42 AS n, 12.34::DECIMAL(18,2) AS d, DATE '2026-10-23' AS day")['rows'], [[42,'12.34','2026-10-23']])
        self.assertEqual(query('SELECT 42 AS n', format='columns')['data'], {'n':[42]})
        limited = query('SELECT * FROM range(1000)', max_rows=3)
        self.assertTrue(limited['truncated'])
        self.assertEqual(limited['row_count'], 3)
        self.assertEqual(query('SELECT * FROM range(1000)')['row_count'], 100)
        request('/query', {'sql':'SELECT missing_column'}, status=400)
        request('/query', {'sql':'SELECT 1','format':'bad'}, status=400)
        self.assertEqual(query('SELECT 1')['rows'], [[1]])

    def test_06_gateway_pg_readonly_and_batch(self):
        self.assertEqual(query('SELECT label FROM pg_rt.public.stable_verify')['rows'], [['updated']])
        request('/query', {'sql':"INSERT INTO pg_rt.public.stable_verify(id) VALUES (3)"}, status=400)
        result = request('/batch', {'sqls':['SELECT 1','SELECT 2']})
        self.assertEqual([r['rows'] for r in result['results']], [[[1]],[[2]]])
        request('/batch', {'sqls':['SELECT nonexistent','CREATE TABLE should_not_exist(i INT)']}, status=400)
        self.assertEqual(query("SELECT count(*) FROM information_schema.tables WHERE table_name='should_not_exist'")['rows'], [[0]])

    def test_07_gateway_write_land_cleanup_failure(self):
        tmp, final = '/data/verify_tmp', '/data/verify_final'
        body = {'sqls':[f"COPY (SELECT 42 AS n) TO '{tmp}/part.parquet' (FORMAT PARQUET)"], 'tmp_dir':tmp,'final_dir':final}
        result = request('/write', body)
        self.assertGreater(result['size_bytes'], 0)
        self.assertEqual(query(f"SELECT * FROM read_parquet('{final}/*.parquet')")['rows'], [[42]])
        request('/write', {**body, 'sqls':['SELECT missing_column']}, status=400)
        self.assertEqual(query(f"SELECT * FROM read_parquet('{final}/*.parquet')")['rows'], [[42]])
        request('/write', {**body, 'land':False})
        self.assertGreater(request('/write-land', {'tmp_dir':tmp,'final_dir':final})['size_bytes'], 0)
        request('/write', {**body, 'land':False})
        self.assertTrue(request('/write-cleanup', {'dir':tmp})['cleaned'])
        self.assertEqual(query(f"SELECT count(*) FROM glob('{tmp}/*')")['rows'], [[0]])

    def test_08_concurrent_gateway_queries(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: query(f'SELECT {i}')['rows'][0][0], range(24)))
        self.assertEqual(results, list(range(24)))
        self.assertEqual(request('/health')['pool']['active'], 0)


if __name__ == '__main__':
    if os.environ.get('PERSIST_ONLY') == '1':
        assert request('/health')['upstream'] == 'ok'
        assert query('SELECT count(*),sum(i) FROM stable_persist')['rows'] == [[100,4950]]
        assert query("SELECT * FROM read_parquet('/data/verify_final/*.parquet')")['rows'] == [[42]]
        assert query('SELECT label FROM pg_rt.public.stable_verify')['rows'] == [['updated']]
        print('PASS: restart persistence, Parquet, PostgreSQL reattach')
    else:
        unittest.main(verbosity=2)
