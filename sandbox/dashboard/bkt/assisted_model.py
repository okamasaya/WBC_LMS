"""正誤を中心にした実験的BKT拡張。各行を同じ事前確率から独立に評価する。

回答時の自信度は正誤観測の尤度の重み、解説後の理解度はその後の
学習遷移の倍率にだけ使う。補助倍率は手動仮定で、学習・校正済みではない。
"""
from dataclasses import dataclass
from itertools import product
import math
from .model import BKTParameters, update as classic_update
from .learning_data import boolean, MAX_ROWS

MODEL_VERSION = 'bkt-assisted-flat-v1'
CONFIDENCE_LABELS = {1: '自信がある', 2: '少し自信がある', 3: 'やや不安', 4: '直感に近い'}
UNDERSTANDING_LABELS = {0: '全然分からない', 1: 'まだ少し分からない', 2: 'だいたい理解できた', 3: '理解できた'}


@dataclass(frozen=True)
class AuxiliaryAssumptions:
    confidence_weights: tuple = (1.5, 1.0, 0.75, 0.5)  # 生値1→4。1が最も自信あり。
    understanding_scales: tuple = (0.25, 0.5, 0.75, 1.0)  # 生値0→3。未入力とは別。

    def __post_init__(self):
        for name in ('confidence_weights', 'understanding_scales'):
            try:
                values = tuple(getattr(self, name))
            except TypeError as error:
                raise ValueError(f'{name}は4個の数値で指定してください。') from error
            if len(values) != 4 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
                raise ValueError(f'{name}は4個の有限な数値で指定してください。')
            if name == 'confidence_weights' and any(x <= 0 for x in values):
                raise ValueError('自信度の重みは0より大きくしてください。')
            if name == 'understanding_scales' and any(not 0 <= x <= 1 for x in values):
                raise ValueError('理解度の倍率は0〜1にしてください。')
            object.__setattr__(self, name, values)


def level(value, allowed, name):
    if value is None or (isinstance(value, str) and value.strip().lower() in ('', 'null', 'none')):
        return None
    if isinstance(value, bool):
        raise ValueError(f'{name}は段階の数値で指定してください。')
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'{name}が数値ではありません。') from error
    if not math.isfinite(number) or number not in allowed:
        raise ValueError(f'{name}は{list(allowed)}で指定してください。')
    return int(number)


def update_flat(correct, confidence=None, understanding=None, parameters=None, assumptions=None):
    parameters = parameters or BKTParameters()
    assumptions = assumptions or AuxiliaryAssumptions()
    # 標準BKTの検証と比較値。補助項目を同じ回答の正答予測へ逆流させない。
    predicted, classic_posterior, classic_after = classic_update(parameters.p_l0, correct, parameters)
    confidence = level(confidence, range(1, 5), '自信度')
    understanding = level(understanding, range(4), '理解度')
    weight = 1.0 if confidence is None else assumptions.confidence_weights[confidence - 1]
    learning_scale = 1.0 if understanding is None else assumptions.understanding_scales[understanding]
    if weight == 1:
        posterior = classic_posterior
    else:
        known = 1 - parameters.p_s if correct else parameters.p_s
        unknown = parameters.p_g if correct else 1 - parameters.p_g
        if parameters.p_l0 == 0 or known == 0:
            posterior = 0.0
        elif parameters.p_l0 == 1 or unknown == 0:
            posterior = 1.0
        else:
            log_odds = math.log(parameters.p_l0) - math.log1p(-parameters.p_l0)
            log_odds += weight * (math.log(known) - math.log(unknown))
            # 極端な重みでもexpのオーバーフローを起こさない。
            posterior = 1 / (1 + math.exp(-log_odds)) if log_odds >= 0 else math.exp(log_odds) / (1 + math.exp(log_odds))
    effective_learning = parameters.p_t * learning_scale
    after = posterior + (1 - posterior) * effective_learning
    return {
        'IsCorrect': correct, 'ConfidenceLevel': confidence, 'UnderstandingLevel': understanding,
        'ObservationWeight': weight, 'LearningScale': learning_scale,
        'PBefore': parameters.p_l0, 'PredictedCorrect': predicted,
        'ClassicPosterior': classic_posterior, 'ClassicAfterLearning': classic_after,
        'AssistedPosterior': posterior, 'EffectiveLearning': effective_learning,
        'AssistedAfterLearning': after,
        'NextCorrect': after * (1 - parameters.p_s) + (1 - after) * parameters.p_g,
        'ConfidenceMissing': confidence is None, 'UnderstandingMissing': understanding is None,
        'ModelVersion': MODEL_VERSION, 'ParameterSource': 'manual_assumption',
    }


def combinations():
    """2×4×4=32通りの設計確認。実際の学習者の観測ではない。"""
    return [{'ResultID': f'SYNTHETIC-{int(correct)}-{confidence}-{understanding}', 'IsAnswered': True,
             'IsCorrect': correct, 'ConfidenceLevel': confidence, 'UnderstandingLevel': understanding}
            for correct, confidence, understanding in product([False, True], range(1, 5), range(4))]


def estimate_flat(records, parameters=None, assumptions=None):
    """履歴・StudentID・SkillIDを使わず、各回答を同じP(L0)から評価する。

    補助項目の空欄は倍率1（補助なし）。不正値・未回答は理由付き除外。
    同じResultIDで3項目や学習者・スキルが競合する版は明示的に拒否する。
    """
    if len(records) > MAX_ROWS:
        raise ValueError(f'入力は{MAX_ROWS:,}行以下にしてください。')
    parameters = parameters or BKTParameters()
    assumptions = assumptions or AuxiliaryAssumptions()
    rows, excluded, seen, patterns = [], [], {}, {}
    for index, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            excluded.append({'Row': index, 'ResultID': '', 'Reason': '入力行は項目名を持つ辞書にしてください。'})
            continue
        result_id = str(raw.get('ResultID') or '').strip()
        try:
            if not boolean(raw.get('IsAnswered', True)):
                excluded.append({'Row': index, 'ResultID': result_id, 'Reason': '未回答（推定しない）'})
                continue
            correct = boolean(raw.get('IsCorrect'))
            confidence = level(raw.get('ConfidenceLevel'), range(1, 5), '自信度')
            understanding = level(raw.get('UnderstandingLevel'), range(4), '理解度')
            key = (correct, confidence, understanding)
            # 独立回答では同じ3項目は同じ推定値。1回の呼出し内だけで再利用する。
            if key not in patterns:
                patterns[key] = update_flat(correct, confidence, understanding, parameters, assumptions)
            result = patterns[key]
        except (ValueError, TypeError) as error:
            excluded.append({'Row': index, 'ResultID': result_id, 'Reason': str(error)})
            continue
        identity = (raw.get('StudentID'), raw.get('SkillID'), correct, result['ConfidenceLevel'], result['UnderstandingLevel'])
        if result_id and result_id in seen:
            if seen[result_id] != identity:
                raise ValueError(f'ResultID {result_id} の正誤・自信度・理解度または識別情報が競合しています。採用する版を確認してください。')
            excluded.append({'Row': index, 'ResultID': result_id, 'Reason': '同じ3項目の重複'})
            continue
        if result_id:
            seen[result_id] = identity
        rows.append({**raw, **result, 'IsAnswered': True, 'Row': index, 'ResultID': result_id or None})
    return {'records': rows, 'excluded': excluded, 'input_count': len(records),
            'model_version': MODEL_VERSION, 'parameter_source': 'manual_assumption',
            'parameters': {'p_l0': parameters.p_l0, 'p_t': parameters.p_t, 'p_g': parameters.p_g, 'p_s': parameters.p_s},
            'assumptions': {'confidence_weights': list(assumptions.confidence_weights), 'understanding_scales': list(assumptions.understanding_scales)}}
