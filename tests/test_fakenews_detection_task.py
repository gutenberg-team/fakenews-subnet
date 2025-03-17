from substrateinterface import Keypair

from fakenews.validator.task.fakenews_detection_with_original import FakenewsDetectionWithOriginal

TEST_API_KEY = "test_api_key"
TEST_KEYPAIR = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())


def test_select_sampled_prompts_1_fake_1_original():
    task = FakenewsDetectionWithOriginal(TEST_API_KEY, TEST_KEYPAIR)

    selected_prompts = [task._select_sampled_prompts_1_fake_1_original() for _ in range(10)]

    for prompts in selected_prompts:
        labels = [p.LABEL_PROBABILITY for p in prompts]
        assert 1.0 in labels
        assert 0.0 in labels
        assert len(prompts) == 2

    # assert that all items are unique
    assert any(
        prompts != selected_prompts[0] for prompts in selected_prompts
    )
