/* A session owns its fixed exercise. Time after answer confirmation is not response time. */
export class DrillSession {
    constructor(exercise, { useConfidence = true, clock = Date.now } = {}) {
        if (!exercise?.questions?.length) throw new Error('出題する問題がありません');
        this.exercise = exercise;
        this.useConfidence = Boolean(useConfidence);
        this.clock = clock;
        this.startedAt = clock();
        this.lastTick = this.startedAt;
        this.endedAt = null;
        this.index = 0;
        this.answers = exercise.questions.map(() => ({ selected: null, confidence: null, confirmed: false, elapsedTimeMs: 0, answeredAt: null }));
    }
    get active() { return this.endedAt === null; }
    get currentAnswer() { return this.answers[this.index]; }
    tick() {
        if (!this.active) return;
        const now = this.clock();
        if (!this.currentAnswer.confirmed) this.currentAnswer.elapsedTimeMs += Math.max(0, now - this.lastTick);
        this.lastTick = now;
    }
    select(position) {
        if (!this.active || this.currentAnswer.confirmed) return false;
        if (!Number.isInteger(position) || position < 0 || position >= 4) throw new Error('回答位置が不正です');
        this.tick();
        this.currentAnswer.selected = position;
        if (!this.useConfidence) this.confirm(null);
        return true;
    }
    confirm(confidence) {
        if (!this.active || this.currentAnswer.confirmed || this.currentAnswer.selected === null) return false;
        if (this.useConfidence && ![1, 2, 3, 4].includes(confidence)) throw new Error('自信度は1〜4から選択してください');
        this.tick();
        Object.assign(this.currentAnswer, { confidence: this.useConfidence ? confidence : null, confirmed: true, answeredAt: new Date(this.lastTick).toISOString() });
        return true;
    }
    move(index) {
        if (!this.active) return;
        if (!Number.isInteger(index) || index < 0 || index >= this.answers.length) throw new Error('問題位置が不正です');
        this.tick();
        this.index = index;
    }
    finish() {
        if (!this.active) return;
        this.tick();
        this.endedAt = this.lastTick;
    }
}
