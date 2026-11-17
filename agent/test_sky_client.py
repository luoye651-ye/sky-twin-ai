"""Offline fixtures only; they do not establish real Java connectivity."""
import os
import unittest
from unittest.mock import Mock, patch
import httpx
from sky_client import AIRCRAFT_URL, SkyReadError, get_aircraft, get_platform_token

ROW = {"id":"fixture-A1","name":"测试样例，非真实飞机","type":"drone","model":"fixture","status":"idle","battery":90,"payloadCapacity":2,"seats":0}


class SkyClientTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ,{"SKYTWIN_TOKEN":"unit-test-token"})
        environment.start()
        self.addCleanup(environment.stop)

    def response(self,payload,status=200):
        return httpx.Response(status,json=payload,request=httpx.Request('GET',AIRCRAFT_URL))

    def test_success_fixed_get_and_field_allowlist(self):
        with patch('sky_client.httpx.get',return_value=self.response({"code":200,"data":[dict(ROW,privateField='hidden')]})) as request:
            rows = get_aircraft()
        self.assertEqual(rows[0]['id'],'fixture-A1')
        self.assertNotIn('privateField',rows[0])
        args,kwargs = request.call_args
        self.assertEqual(args,(AIRCRAFT_URL,))
        self.assertEqual(kwargs['headers'],{'Authorization':'Bearer unit-test-token'})
        self.assertFalse(kwargs['trust_env'])
        self.assertFalse(kwargs['follow_redirects'])
        self.assertEqual(kwargs['timeout'],10)

    def test_empty_list_is_valid(self):
        with patch('sky_client.httpx.get',return_value=self.response({'code':200,'data':[]})):
            self.assertEqual(get_aircraft(),[])

    def test_missing_token_prevents_request_and_fallback(self):
        with patch.dict(os.environ,{'SKYTWIN_TOKEN':''}),patch('sky_client.httpx.get') as request,patch('sky_client.dotenv_values') as config:
            with self.assertRaises(SkyReadError): get_aircraft()
            request.assert_not_called()
            config.assert_not_called()

    def test_bad_token_format_rejected(self):
        for token in ('Bearer token','some\r\ntoken'):
            with self.subTest(case='invalid'),patch.dict(os.environ,{'SKYTWIN_TOKEN':token}):
                with self.assertRaises(SkyReadError): get_platform_token()

    def test_authentication_http_and_business_errors(self):
        for status,code in ((401,401),(403,403),(200,401),(200,403),(200,500)):
            with self.subTest(status=status,code=code),patch('sky_client.httpx.get',return_value=self.response({'code':code,'msg':'secret-raw-response'},status)):
                with self.assertRaises(SkyReadError) as caught: get_aircraft()
                self.assertNotIn('secret-raw-response',str(caught.exception))
                self.assertNotIn('unit-test-token',str(caught.exception))

    def test_redirect_rejected(self):
        with patch('sky_client.httpx.get',return_value=self.response({},302)):
            with self.assertRaises(SkyReadError): get_aircraft()

    def test_schema_errors(self):
        for payload in ([],{'code':'secret'},{'code':True},{'code':200,'data':{}},{'code':200,'data':[{}]}):
            with self.subTest(payload_kind=type(payload).__name__),patch('sky_client.httpx.get',return_value=self.response(payload)):
                with self.assertRaises(SkyReadError): get_aircraft()

    def test_invalid_values(self):
        for battery in (-1,101,'bad',float('nan')):
            response = Mock(status_code=200)
            response.json.return_value = {'code':200,'data':[dict(ROW,battery=battery)]}
            with self.subTest(case='invalid battery'),patch('sky_client.httpx.get',return_value=response):
                with self.assertRaises(SkyReadError): get_aircraft()

    def test_non_json_error(self):
        response = httpx.Response(200,text='<html>secret</html>',request=httpx.Request('GET',AIRCRAFT_URL))
        with patch('sky_client.httpx.get',return_value=response):
            with self.assertRaises(SkyReadError): get_aircraft()

    def test_timeout_and_connection_do_not_leak_raw_error(self):
        for error in (httpx.ReadTimeout('unit-test-token'),httpx.ConnectError('unit-test-token')):
            with self.subTest(error_type=type(error).__name__),patch('sky_client.httpx.get',side_effect=error):
                with self.assertRaises(SkyReadError) as caught: get_aircraft()
                self.assertNotIn('unit-test-token',str(caught.exception))


if __name__ == '__main__': unittest.main()
