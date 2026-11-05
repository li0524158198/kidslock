import { util } from '@kit.ArkTS';
import { common } from '@kit.AbilityKit';
import { fileIo as fs } from '@kit.CoreFileKit';

/** JSON 题目结构 */
interface QuestionRaw {
  q: string;
  opts: string[];
  ans: number;
  char: string | null;
}

/** questions.json 根结构 */
interface QuestionsRoot {
  version: number;
  labels: Record<string, string>;
  banks: Record<string, QuestionRaw[]>;
}

/** 出题结果 */
export class Question {
  text: string = '';
  bigChar: string | null = null; // 字音题大字
  options: string[] = [];
  answerIndex: number = 0;
}

/** 自定义库持久化 JSON 条目 */
interface CustomBankEntryJson {
  id: string;
  label: string;
  items: QuestionRaw[];
}

/** 自定义题库（CSV 导入）条目 */
interface CustomBankEntry {
  label: string;
  items: QuestionRaw[];
}

/**
 * 人教版语数英题库引擎（1-12 年级 × 3 学科 = 36 内置库）。
 * 内置题来自 rawfile/questions.json（三平台共享）；
 * 数学按年级程序生成；支持自定义题库（CSV 导入，应用沙箱持久化）。
 */
export class QuestionBank {
  static readonly SUBJECTS: string[] = ['chinese', 'math', 'english'];
  static readonly SUBJECT_NAMES: string[] = ['语文', '数学', '英语'];
  static readonly GRADE_NAMES: string[] =
    ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
      '初一', '初二', '初三', '高一', '高二', '高三'];
  static readonly CUSTOM_PREFIX: string = 'custom_';

  private banks: Record<string, QuestionRaw[]> = {};
  private labels: Record<string, string> = {};
  private customBanks: Record<string, CustomBankEntry> = {};
  private loaded: boolean = false;
  private context: common.UIAbilityContext;

  constructor(context: common.UIAbilityContext) {
    this.context = context;
    this.loadBuiltin();
    this.loadCustom();
  }

  private loadBuiltin(): void {
    try {
      const raw: Uint8Array = this.context.resourceManager.getRawFileContentSync('questions.json');
      const decoder: util.TextDecoder = util.TextDecoder.create('utf-8');
      const text: string = decoder.decodeToString(raw);
      const root = JSON.parse(text) as QuestionsRoot;
      this.banks = root.banks;
      this.labels = root.labels;
      this.loaded = true;
    } catch (e) {
      console.error('QuestionBank load failed: ' + JSON.stringify(e));
    }
  }

  // ==================== 题库清单 ====================

  /** 内置库数量（36） */
  static get builtinCount(): number {
    return 36;
  }

  /** 内置库显示名 */
  static builtinLabel(subject: number, grade: number): string {
    return `${QuestionBank.SUBJECT_NAMES[subject]}·${QuestionBank.GRADE_NAMES[grade]}`;
  }

  static builtinId(subject: number, grade: number): string {
    return `${QuestionBank.SUBJECTS[subject]}_g${grade + 1}`;
  }

  /** 全部自定义库 id */
  getCustomIds(): string[] {
    return Object.keys(this.customBanks);
  }

  getCustomLabel(id: string): string {
    const e = this.customBanks[id];
    return e ? e.label : id;
  }

  getLabel(bankId: string): string {
    const id = this.resolveBankId(bankId);
    if (this.customBanks[id] !== undefined) {
      return this.customBanks[id].label;
    }
    const v = this.labels[id];
    return v === undefined ? id : v;
  }

  /** 兼容旧版三级库 id：primary→g5、junior→g7、senior→g10 */
  resolveBankId(bankId: string): string {
    if (bankId !== undefined && bankId !== null && bankId.length > 0) {
      if (bankId.startsWith(QuestionBank.CUSTOM_PREFIX) && this.customBanks[bankId] !== undefined) {
        return bankId;
      }
      if (this.banks[bankId] !== undefined) {
        return bankId;
      }
      if (bankId.endsWith('_primary')) {
        return bankId.replace('_primary', '_g5');
      }
      if (bankId.endsWith('_junior')) {
        return bankId.replace('_junior', '_g7');
      }
      if (bankId.endsWith('_senior')) {
        return bankId.replace('_senior', '_g10');
      }
    }
    return 'chinese_g1';
  }

  // ==================== 出题 ====================

  getQuestion(bankId: string): Question {
    const id = this.resolveBankId(bankId);
    try {
      if (id.startsWith(QuestionBank.CUSTOM_PREFIX) && this.customBanks[id] !== undefined) {
        const items = this.customBanks[id].items;
        const item = items[Math.floor(Math.random() * items.length)];
        return QuestionBank.shuffle(item.q, item.char, item.opts, item.ans);
      }
      const grade = this.parseGrade(id);
      if (id.startsWith('math') && grade >= 1 && grade <= 9 && Math.random() < 0.3) {
        const gq = this.genMath(grade);
        if (gq !== null) {
          return gq;
        }
      }
      const arr = this.banks[id];
      if (arr === undefined || arr.length === 0) {
        throw new Error('empty bank ' + id);
      }
      const item = arr[Math.floor(Math.random() * arr.length)];
      return QuestionBank.shuffle(item.q, item.char, item.opts, item.ans);
    } catch (e) {
      const q = new Question();
      q.text = '出题出错，请重试';
      q.options = ['1', '2', '3', '4'];
      return q;
    }
  }

  private parseGrade(bankId: string): number {
    const i = bankId.indexOf('_g');
    if (i >= 0) {
      const n = parseInt(bankId.substring(i + 2));
      return Number.isNaN(n) ? -1 : n;
    }
    return -1;
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
    for (let i = q.options.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = q.options[i];
      q.options[i] = q.options[j];
      q.options[j] = t;
    }
    const idx = q.options.indexOf(correct);
    q.answerIndex = idx >= 0 ? idx : 0;
    return q;
  }

  private static ri(min: number, max: number): number {
    return min + Math.floor(Math.random() * (max - min + 1));
  }

  // ==================== 数学按年级生成 ====================

  private genMath(grade: number): Question | null {
    if (grade <= 2) {
      if (Math.random() < 0.5) {
        const a = QuestionBank.ri(grade === 1 ? 1 : 11, grade === 1 ? 10 : 89);
        const b = QuestionBank.ri(1, grade === 1 ? 10 : 89);
        return QuestionBank.buildNumeric(`${a} + ${b} = ?`, a + b);
      }
      const a = QuestionBank.ri(grade === 1 ? 2 : 30, grade === 1 ? 10 : 99);
      const b = QuestionBank.ri(1, a - 1);
      return QuestionBank.buildNumeric(`${a} - ${b} = ?`, a - b);
    }
    if (grade <= 4) {
      const b = QuestionBank.ri(3, 9);
      const r = QuestionBank.ri(3, grade <= 3 ? 9 : 40);
      const a = b * r;
      return Math.random() < 0.5
        ? QuestionBank.buildNumeric(`${a} × ${b} = ?`, a * b)
        : QuestionBank.buildNumeric(`${a} ÷ ${b} = ?`, r);
    }
    if (grade <= 6) {
      const a = QuestionBank.ri(11, 60);
      const b = QuestionBank.ri(2, 20);
      // 五六年级未学负数：c 不超过 a+b-1，保证结果 ≥ 1
      const c = QuestionBank.ri(5, Math.min(40, a + b - 1));
      return QuestionBank.buildNumeric(`${a} + ${b} - ${c} = ?`, a + b - c);
    }
    const a = QuestionBank.ri(2, 9);
    const x = QuestionBank.ri(1, 15);
    const b = QuestionBank.ri(1, 40);
    return QuestionBank.buildNumeric(`解方程：${a}x + ${b} = ${a * x + b}，x = ?`, x);
  }

  private static buildNumeric(text: string, r: number): Question {
    const set: Set<number> = new Set<number>();
    set.add(r);
    while (set.size < 4) {
      const d = QuestionBank.ri(1, 9) * (Math.random() < 0.125 ? 10 : 1);
      const v = r + (Math.random() < 0.5 ? d : -d);
      if (v >= 0) {
        set.add(v);
      }
    }
    const vals = Array.from(set);
    for (let i = vals.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = vals[i];
      vals[i] = vals[j];
      vals[j] = t;
    }
    const q = new Question();
    q.text = text;
    q.options = vals.map(v => v.toString());
    const idx = q.options.indexOf(r.toString());
    q.answerIndex = idx >= 0 ? idx : 0;
    return q;
  }

  // ==================== CSV 导入导出 ====================

  /** 导出某库为 CSV 文本（字段含逗号/引号/换行时按 RFC 4180 加双引号包裹） */
  exportCsv(bankId: string): string {
    const id = this.resolveBankId(bankId);
    let items: QuestionRaw[] = [];
    if (id.startsWith(QuestionBank.CUSTOM_PREFIX) && this.customBanks[id] !== undefined) {
      items = this.customBanks[id].items;
    } else if (this.banks[id] !== undefined) {
      items = this.banks[id];
    }
    const letters: string[] = ['A', 'B', 'C', 'D'];
    let sb = '题干,选项A,选项B,选项C,选项D,答案,大字\r\n';
    for (const it of items) {
      const opts: string[] = [];
      for (let i = 0; i < 4; i++) {
        opts.push((it.opts[i] ?? '').replace(/,/g, '，'));
      }
      const ans = letters[it.ans] ?? 'A';
      const big = it.char ?? '';
      sb += `${QuestionBank.csvCell(it.q)},${QuestionBank.csvCell(opts[0])},${QuestionBank.csvCell(opts[1])},` +
        `${QuestionBank.csvCell(opts[2])},${QuestionBank.csvCell(opts[3])},${ans},${big}\r\n`;
    }
    return sb;
  }

  private static csvCell(s: string): string {
    if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\n') >= 0) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  /**
   * 从 CSV 文本导入为自定义库（覆盖同名）。
   * @return 实际保存的自定义库 id（文件名已净化，调用方必须用该 id 选中题库）
   */
  importCsv(name: string, csvText: string): string {
    const items: QuestionRaw[] = [];
    const rows: string[][] = QuestionBank.parseCsv(csvText);
    let start = 0;
    if (rows.length > 0 && rows[0].length > 0 && rows[0][0].indexOf('题干') >= 0) {
      start = 1;
    }
    for (let i = start; i < rows.length; i++) {
      const c = rows[i];
      if (c.length < 6) {
        continue;
      }
      const q = c[0].trim();
      if (q.length === 0) {
        continue;
      }
      let ans = 0;
      const idx = ['A', 'B', 'C', 'D'].indexOf(c[5].trim().toUpperCase());
      if (idx >= 0) {
        ans = idx;
      }
      items.push({
        q: q,
        opts: [c[1].trim(), c[2].trim(), c[3].trim(), c[4].trim()],
        ans: ans,
        char: c.length > 6 && c[6].trim().length > 0 ? c[6].trim() : null,
      });
    }
    if (items.length === 0) {
      throw new Error('没有解析到有效题目');
    }
    const safe = name.replace(/[\\/:*?"<>|]/g, '_');
    const id = QuestionBank.CUSTOM_PREFIX + safe;
    this.customBanks[id] = { label: `自定义·${safe}`, items: items };
    this.saveCustom();
    return id;
  }

  /** 某题库的题目数（内置库或自定义库；导入成功的题数用它取） */
  bankSize(bankId: string): number {
    const id = this.resolveBankId(bankId);
    if (id.startsWith(QuestionBank.CUSTOM_PREFIX)) {
      const e = this.customBanks[id];
      return e !== undefined ? e.items.length : 0;
    }
    const arr = this.banks[id];
    return arr !== undefined ? arr.length : 0;
  }

  /** 极简 CSV 解析：支持双引号包裹与转义、引号内逗号/换行、\r\n 换行、BOM */
  private static parseCsv(text: string): string[][] {
    const rows: string[][] = [];
    let cur: string[] = [];
    let cell = '';
    let inQuote = false;
    const s = text.replace(/\uFEFF/g, '');
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (inQuote) {
        if (ch === '"') {
          if (i + 1 < s.length && s[i + 1] === '"') {
            cell += '"';
            i++;
          } else {
            inQuote = false;
          }
        } else {
          cell += ch;
        }
      } else if (ch === '"') {
        inQuote = true;
      } else if (ch === ',') {
        cur.push(cell);
        cell = '';
      } else if (ch === '\n') {
        cur.push(cell);
        rows.push(cur);
        cur = [];
        cell = '';
      } else if (ch !== '\r') {
        cell += ch;
      }
    }
    if (cell.length > 0 || cur.length > 0) {
      cur.push(cell);
      rows.push(cur);
    }
    return rows;
  }

  private customFile(): string {
    return this.context.filesDir + '/custom_banks.json';
  }

  private saveCustom(): void {
    try {
      const entries: CustomBankEntryJson[] = [];
      const ids = Object.keys(this.customBanks);
      for (const id of ids) {
        const e = this.customBanks[id];
        entries.push({ id: id, label: e.label, items: e.items } as CustomBankEntryJson);
      }
      const text = JSON.stringify(entries);
      const file = fs.openSync(this.customFile(), fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE | fs.OpenMode.TRUNC);
      fs.writeSync(file.fd, text);
      fs.closeSync(file);
    } catch (e) {
      console.error('saveCustom failed: ' + JSON.stringify(e));
    }
  }

  private loadCustom(): void {
    try {
      const file = fs.openSync(this.customFile(), fs.OpenMode.READ_ONLY);
      const stat = fs.statSync(file.fd);
      const buf = new ArrayBuffer(stat.size);
      fs.readSync(file.fd, buf);
      fs.closeSync(file);
      const text = util.TextDecoder.create('utf-8').decodeToString(new Uint8Array(buf));
      const arr = JSON.parse(text) as CustomBankEntryJson[];
      for (const e of arr) {
        this.customBanks[e.id] = { label: e.label, items: e.items } as CustomBankEntry;
      }
    } catch (e) {
      // 首次没有自定义库，忽略
    }
  }
}
