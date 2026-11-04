import { util } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';

/**
 * 人教版语数英题库引擎（小学/初中/高中 × 3 学科）。
 * 内置题来自 rawfile/questions.json（三平台共享同一份数据）；
 * 小学/初中数学额外程序生成，可无限出题。
 */
export class Question {
  text: string = '';
  bigChar: string | null = null; // 字音题大字
  options: string[] = [];
  answerIndex: number = 0;
}

export class QuestionBank {
  static readonly BANK_IDS: string[] = [
    'chinese_primary', 'math_primary', 'english_primary',
    'chinese_junior', 'math_junior', 'english_junior',
    'chinese_senior', 'math_senior', 'english_senior',
  ];
  private banks: Record<string, object> = {};
  private labels: Record<string, string> = {};
  private loaded: boolean = false;

  constructor(context: common.UIAbilityContext) {
    this.load(context);
  }

  private load(context: common.UIAbilityContext): void {
    try {
      const raw = context.resourceManager.getRawFileContentSync('questions.json');
      const decoder = util.TextDecoder.create('utf-8');
      const text = decoder.decodeToString(new Uint8Array(raw.buffer as ArrayBuffer));
      const root: Record<string, object> = JSON.parse(text) as Record<string, object>;
      this.banks = root.banks as Record<string, object>;
      this.labels = root.labels as Record<string, string>;
      this.loaded = true;
    } catch (e) {
      console.error('QuestionBank load failed: ' + JSON.stringify(e));
    }
  }

  getLabel(bankId: string): string {
    const v = this.labels[bankId];
    return v === undefined ? bankId : v;
  }

  /** 取一道题（随机 + 选项打乱；小学/初中数学 50% 概率动态生成） */
  getQuestion(bankId: string): Question {
    if (!this.loaded) {
      const q = new Question(); q.text = '题库加载失败';
      q.options = ['1', '2', '3', '4'];
      return q;
    }
    if (bankId === 'math_primary' && Math.random() < 0.5) {
      return QuestionBank.genPrimaryMath();
    }
    if (bankId === 'math_junior' && Math.random() < 0.5) {
      return QuestionBank.genJuniorEquation();
    }
    try {
      const arr = this.banks[bankId] as Array<Record<string, object>>;
      const item = arr[Math.floor(Math.random() * arr.length)];
      return QuestionBank.shuffle(item.q as string,
        (item.char as string) ?? null,
        item.opts as string[],
        item.ans as number);
    } catch (e) {
      const q = new Question(); q.text = '出题出错，请重试';
      q.options = ['1', '2', '3', '4'];
      return q;
    }
  }

  private static shuffle(text: string, bigChar: string | null, optsArr: string[], ansIdx: number): Question {
    const q = new Question();
    q.text = text;
    q.bigChar = bigChar;
    const correct = optsArr[ansIdx];
    const seen: Set<string> = new Set<string>();
    q.options = [];
    for (const o of optsArr) {
      const t = o.trim();
      if (t.length > 0 && !seen.has(t) && q.options.length < 4) {
        seen.add(t);
        q.options.push(t);
      }
    }
    while (q.options.length < 4) {
      q.options.push('—');
    }
    // 打乱
    for (let i = q.options.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = q.options[i]; q.options[i] = q.options[j]; q.options[j] = t;
    }
    q.answerIndex = q.options.indexOf(correct);
    if (q.answerIndex < 0) { q.answerIndex = 0; }
    return q;
  }

  private static ri(min: number, max: number): number {
    return min + Math.floor(Math.random() * (max - min + 1));
  }

  /** 小学数学四则运算 */
  private static genPrimaryMath(): Question {
    const op = Math.floor(Math.random() * 4);
    let a: number, b: number, r: number, sym: string;
    if (op === 0) { a = QuestionBank.ri(12, 89); b = QuestionBank.ri(12, 89); r = a + b; sym = '+'; }
    else if (op === 1) { a = QuestionBank.ri(30, 99); b = QuestionBank.ri(11, a - 1); r = a - b; sym = '-'; }
    else if (op === 2) { a = QuestionBank.ri(3, 12); b = QuestionBank.ri(3, 12); r = a * b; sym = '×'; }
    else { b = QuestionBank.ri(3, 9); r = QuestionBank.ri(3, 12); a = b * r; sym = '÷'; }
    return QuestionBank.buildNumeric(`${a} ${sym} ${b} = ?`, r);
  }

  /** 初中一元一次方程 */
  private static genJuniorEquation(): Question {
    const a = QuestionBank.ri(2, 9), x = QuestionBank.ri(1, 12), b = QuestionBank.ri(1, 30);
    const c = a * x + b;
    return QuestionBank.buildNumeric(`解方程：${a}x + ${b} = ${c}，x = ?`, x);
  }

  private static buildNumeric(text: string, r: number): Question {
    const set: Set<number> = new Set<number>();
    set.add(r);
    while (set.size < 4) {
      const d = QuestionBank.ri(1, 9) * (Math.random() < 0.1 ? 10 : 1);
      const v = r + (Math.random() < 0.5 ? d : -d);
      if (v >= 0) { set.add(v); }
    }
    const vals = Array.from(set);
    for (let i = vals.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = vals[i]; vals[i] = vals[j]; vals[j] = t;
    }
    const q = new Question();
    q.text = text;
    q.options = vals.map(v => v.toString());
    q.answerIndex = q.options.indexOf(r.toString());
    if (q.answerIndex < 0) { q.answerIndex = 0; }
    return q;
  }
}
