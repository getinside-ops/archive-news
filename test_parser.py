"""Self-checking tests, no framework: python test_parser.py"""
import json
import tempfile

from src.generator import _script_json
from src.parser import EmailParser, is_unsubscribe_link, redact_url


def test_unsubscribe_links_are_redacted_and_never_resolved():
    html = ('<html><body>'
            '<a href="https://shop.example/promo?id=1">Voir la promo</a>'
            '<a href="https://trk.example/l/SECRET_TOKEN">Se désinscrire</a>'
            '<a href="https://esp.example/unsubscribe?u=SECRET">ici</a>'
            '</body></html>')
    with tempfile.TemporaryDirectory() as tmp:
        parser = EmailParser(html, tmp)
        parser.clean_and_process()
        out = parser.get_html()
    assert 'SECRET' not in out and 'SECRET' not in json.dumps(parser.links)
    assert [l['is_unsubscribe'] for l in parser.links] == [False, True, True]
    assert parser.links[1]['original_url'] == 'https://trk.example/'
    assert parser.audit['unsubscribe_found'] is True
    assert 'https://shop.example/promo?id=1' in out  # normal links untouched


def test_unsubscribe_detection():
    assert is_unsubscribe_link('Vous désabonner', 'https://x.example/l/abc')
    assert is_unsubscribe_link('cliquez ici', 'https://x.example/p/Unsubscribe?a=1')
    assert is_unsubscribe_link('Opt-out', 'https://x.example/')
    assert not is_unsubscribe_link('Découvrir', 'https://x.example/nouveautes')
    assert redact_url('${unsubscribe}') == '#'


def test_inline_json_cannot_close_the_script_tag():
    payload = '</SCRIPT ><script>alert(1)</script><!--'
    out = _script_json(payload)
    assert '<' not in out
    assert json.loads(out) == payload


def test_cid_image_is_localized():
    gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    with tempfile.TemporaryDirectory() as tmp:
        parser = EmailParser('<html><body><img src="cid:img1"></body></html>', tmp, attachments={'img1': gif})
        parser.download_images_parallel()
        assert 'src="img_0.gif"' in parser.get_html()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(f"{len(tests)} tests passed")
