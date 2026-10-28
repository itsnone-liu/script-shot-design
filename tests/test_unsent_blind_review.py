import json,tempfile,unittest
from pathlib import Path
from experiments.build_unsent_blind_review import build_bundle

class BlindBundleTest(unittest.TestCase):
    def test_public_has_no_source_identifiers_or_seed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);media=root/'UNSENT_P2_A_T1.mp4';media.write_bytes(b'fake media for unit test only')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'takes':[{'shot_id':'UNSENT_P2_A_T1','pass':2,'status':'success','outputs':[str(media)]}]}),encoding='utf-8')
            pub=root/'public';priv=root/'private';result=build_bundle(manifest,pub,priv,1234567)
            text=(pub/'review.md').read_text(encoding='utf-8')
            self.assertNotIn('UNSENT',text);self.assertNotIn('1234567',text);self.assertFalse((pub/'mapping.json').exists())
            self.assertEqual((pub/'V001.mp4').read_bytes(),media.read_bytes());self.assertEqual(result['count'],1)
            self.assertEqual(json.loads((priv/'mapping.json').read_text(encoding='utf-8'))['entries'][0]['take']['pass'],2)
            with self.assertRaises(ValueError):build_bundle(manifest,pub,priv,1)

    def test_private_cannot_be_inside_public(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError):build_bundle(root/'manifest',root/'public',root/'public/private',1)

    def test_missing_media_creates_no_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);m=root/'m.json';m.write_text(json.dumps({'takes':[{'shot_id':'x','status':'success','outputs':['missing.mp4']}]}),encoding='utf-8')
            with self.assertRaises(FileNotFoundError):build_bundle(m,root/'public',root/'private',1)
            self.assertFalse((root/'public').exists())

if __name__=='__main__':unittest.main()
