"""setup.py 키 저장소(파일 백엔드)·localnet 관문 검사 — 네트워크·Jev 호출 없음. python3 test_setup_local.py"""
import os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev, localnet  # noqa: E402


class KeyStore(unittest.TestCase):
    def test_file_backend_roundtrip(self):  # 키체인·자격 증명 관리자를 끄고 파일 저장소만(모든 OS 공통 경로)
        import jev
        d = tempfile.mkdtemp()
        saved = (jev._mac, jev._win_write, jev._win_read, jev._win_delete, jev.KEY_DIR)
        try:
            jev._mac, jev._win_write, jev._win_read, jev._win_delete = (lambda: False), (lambda t, a, v: False), (lambda t: None), (lambda t: False)
            jev.KEY_DIR = jev.Path(d)
            f = jev.Path(d) / 'typesafe-jev' / 'key'
            self.assertEqual(jev.save_key(' test-key-0123456789 '), str(f))
            self.assertEqual(jev.stored_key()[0], 'test-key-0123456789')
            if os.name != 'nt':
                self.assertEqual(os.stat(f).st_mode & 0o777, 0o600)
            fish = jev.save_secret('fish-audio', 'FISH_AUDIO_API_KEY', 'fish-key-0123456789')  # 서비스마다 따로
            self.assertTrue(fish.endswith(os.path.join('fish-audio', 'key')))
            self.assertEqual(jev.stored_secret('fish-audio', 'FISH_AUDIO_API_KEY')[0], 'fish-key-0123456789')
            self.assertEqual(jev.forget_key(), [str(f)])
            self.assertEqual(jev.stored_key(), (None, ''))
            self.assertEqual(jev.stored_secret('fish-audio', 'FISH_AUDIO_API_KEY')[0], 'fish-key-0123456789')  # 다른 키는 그대로
            with self.assertRaises(jev.JevError):
                jev.save_key('bad\nkey')
        finally:
            jev._mac, jev._win_write, jev._win_read, jev._win_delete, jev.KEY_DIR = saved
            shutil.rmtree(d)


class Gate(unittest.TestCase):
    def test_same_owner_only(self):
        st = {'Self': {'UserID': 1, 'TailscaleIPs': ['100.1.1.1'], 'DNSName': 'edb-mac.tail.ts.net.'},
              'Peer': {'a': {'UserID': 1, 'TailscaleIPs': ['100.2.2.2']}, 'b': {'UserID': 2, 'TailscaleIPs': ['100.3.3.3']}}}
        ip, dns, hosts, peers = localnet.allowlist(st)
        g = localnet.Gate(8765, hosts, peers)
        self.assertTrue(g.allowed('100.2.2.2', 'edb-mac.tail.ts.net:8765'))
        self.assertFalse(g.allowed('100.3.3.3', 'edb-mac.tail.ts.net:8765'))
        self.assertFalse(g.allowed('127.0.0.1', 'evil.com:8765'))

    def test_tagged_nodes(self):  # 태그 기기는 tailnet 공용 UserID — 이 기기에 태그가 있으면 열지 않고, 태그 peer 는 뺀다
        peers = {'t': {'UserID': 1, 'TailscaleIPs': ['100.4.4.4'], 'Tags': ['tag:server']}}
        self.assertTrue(localnet.refuse_reason({'Self': {'UserID': 1, 'TailscaleIPs': ['100.1.1.1'], 'Tags': ['tag:x']}, 'Peer': peers}))
        self.assertNotIn('100.4.4.4', localnet.allowlist({'Self': {'UserID': 1, 'TailscaleIPs': ['100.1.1.1']}, 'Peer': peers})[3])


class Setup(unittest.TestCase):
    def test_motion_asks_jev_and_fish(self):  # narrate/ 가 옆에 있으면 meta-motion — Fish 키도 묻는다
        import setup
        self.assertEqual(setup.plugin_keys(), ['jev', 'fish'])
        self.assertFalse(setup.KEYS['fish']['required'])

    def test_narrate_needs_key_message(self):
        import narrate
        self.assertEqual(narrate.main([]), 2)  # 대본 없으면 사용법


if __name__ == '__main__':
    unittest.main(verbosity=1)
