import importlib.util, pathlib, unittest, torch
ROOT = pathlib.Path(__file__).resolve().parent
S = importlib.util.spec_from_file_location("seamless_worker", ROOT / "seamlessm4t_50mb_lowrank_v1.py")
worker = importlib.util.module_from_spec(S); S.loader.exec_module(worker)
R = importlib.util.spec_from_file_location("seamless_runtime", ROOT / "seamlessm4t_50mb_runtime_v1.py")
runtime = importlib.util.module_from_spec(R); R.loader.exec_module(runtime)
class FakeSlice:
    def __init__(self, tensor): self.tensor = tensor
    def get_shape(self): return tuple(self.tensor.shape)
    def __getitem__(self, item): return self.tensor[item]
class ContractTests(unittest.TestCase):
    def test_hard_cap_and_identity_pins(self):
        self.assertEqual(worker.TARGET_BYTES, 50_000_000)
        self.assertEqual(worker.RANK, 1)
        self.assertEqual(worker.EXPECTED_CONFIG_SHA, "4b2fa9d863cc3033adaf261e6c3e32ad90347ee2f199a349ba1c77d5e26a605f")
        self.assertEqual(worker.EXPECTED_INDEX_SHA, "79d33aa045308d1a93b11952f2a3e6a647c107b688e5fdf1124c4601626dcdb2")
    def test_2d_factorization_contract(self):
        torch.manual_seed(17); tensor=torch.randn(8,6)
        output,metric=worker.tensor_lowrank(FakeSlice(tensor), "test.linear.weight", 1, object())
        self.assertEqual(tuple(output["test.linear.weight_u"].shape),(8,1))
        self.assertEqual(tuple(output["test.linear.weight_v"].shape),(1,6))
        self.assertTrue(all(torch.isfinite(v.float()).all() for v in output.values()))
        self.assertEqual(metric["rank"],1)
    def test_3d_conv_factorization_contract(self):
        torch.manual_seed(19); tensor=torch.randn(4,3,5)
        output,metric=worker.tensor_lowrank(FakeSlice(tensor), "test.conv.weight", 1, object())
        self.assertEqual(tuple(output["test.conv.weight_u"].shape),(4,1))
        self.assertEqual(tuple(output["test.conv.weight_v"].shape),(1,15))
        self.assertTrue(all(torch.isfinite(v.float()).all() for v in output.values()))
        self.assertEqual(metric["shape"],[4,3,5])
    def test_runtime_models_have_required_conv_support(self):
        self.assertTrue(hasattr(runtime,"LowRankLinear"))
        self.assertTrue(hasattr(runtime,"LowRankEmbedding"))
        self.assertTrue(hasattr(runtime,"LowRankConv1d"))
        self.assertIn('seamless_m4t_v2',(ROOT/"seamlessm4t_50mb_runtime_v1.py").read_text())
if __name__=="__main__": unittest.main(verbosity=2)
