// 旧ALPサーバー（8051）用の互換入口。新しいテストはbkt/tests/browser.cjs。
process.env.ALP_TEST_URL ||= 'http://127.0.0.1:8051';
require('../bkt/tests/browser.cjs');
