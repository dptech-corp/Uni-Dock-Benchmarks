from rdkit.ML.Scoring.Scoring import CalcEnrichment


def ef_score(label_list: list[int], score_list: list[float], fraction_list: list[float], sort_flag: bool = False):
    # validation
    assert len(label_list) == len(score_list), 'Number of label and score list not match'
    assert len(fraction_list) > 0, 'need to assign the fractions of enrichment'
    assert all([v in [0,1] for v in label_list]), 'label list should be binary'


    label_score_list = list(zip(label_list, score_list))
    label_score_list = sorted(label_score_list, key=lambda pair: pair[1], reverse=sort_flag)

    return CalcEnrichment(label_score_list, 0, fraction_list)