

def read_unidock_score(result_file:str) -> list[float]:
    score_list = []
    with open(result_file, "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.startswith("> <Uni-Dock RESULT>"):
                score = float(lines[idx + 1].partition(
                    "LOWER_BOUND=")[0][len("ENERGY="):])
                score_list.append(score)
    return score_list