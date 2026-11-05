# -*- coding: utf-8 -*-
"""T4.13 匹配顺序修正：p3(混合)优先+p2 锚定；负数断言拆分"""
path = r'D:\project\kidslock\qa\jvm\src\JvmTests.java'
src = open(path, encoding='utf-8').read()

MUL = chr(215)

old = '''                    long expect; java.util.regex.Matcher m;
                    if ((m = p2.matcher(q.text)).find()) {
                        long a = Long.parseLong(m.group(1)), b = Long.parseLong(m.group(3));
                        String op = m.group(2);
                        if (op.equals("+")) expect = a + b;
                        else if (op.equals("-")) expect = a - b;
                        else if (op.equals("' + MUL + '")) { expect = a * b; mulTotal++; }
                        else expect = a / b;
                        long got = Long.parseLong(q.options.get(q.answerIndex));
                        if (got != expect) {
                            if (op.equals("' + MUL + '")) { mulBad++; if (mulSample.isEmpty()) mulSample = q.text + " marked=" + got + " expect=" + expect; }
                            else { otherBad++; if (otherSample.isEmpty()) otherSample = q.text + " marked=" + got + " expect=" + expect; }
                        }
                    } else if ((m = p3.matcher(q.text)).find()) {
                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(2)) - Long.parseLong(m.group(3));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if ((m = pe.matcher(q.text)).find()) {'''

new = '''                    long expect; java.util.regex.Matcher m;
                    if ((m = p3.matcher(q.text)).matches()) {
                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(2)) - Long.parseLong(m.group(3));
                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }
                    } else if ((m = pe.matcher(q.text)).matches()) {'''

assert old in src, 'T4.13 block not found'
src = src.replace(old, new)

# p2 分支移到方程分支后（重排：p3 → pe → p2）
old2 = '''                    } else { otherBad++; if (otherSample.isEmpty()) otherSample = "unparsed: " + q.text; }'''
new2 = '''                    } else if ((m = p2.matcher(q.text)).matches()) {
                        long a = Long.parseLong(m.group(1)), b = Long.parseLong(m.group(3));
                        String op = m.group(2);
                        if (op.equals("+")) expect = a + b;
                        else if (op.equals("-")) expect = a - b;
                        else if (op.equals("' + MUL + '")) { expect = a * b; mulTotal++; }
                        else expect = a / b;
                        long got = Long.parseLong(q.options.get(q.answerIndex));
                        if (got != expect) {
                            if (op.equals("' + MUL + '")) { mulBad++; if (mulSample.isEmpty()) mulSample = q.text + " marked=" + got + " expect=" + expect; }
                            else { otherBad++; if (otherSample.isEmpty()) otherSample = q.text + " marked=" + got + " expect=" + expect; }
                        }
                    } else { otherBad++; if (otherSample.isEmpty()) otherSample = "unparsed: " + q.text; }'''
assert old2 in src, 'tail not found'
src = src.replace(old2, new2)

# 负数断言拆分：负选项必须且只能是答案；统计负答案次数（P3）
old3 = '''                    if (q.options.stream().anyMatch(o -> o.startsWith("-"))) negOpt++;'''
new3 = '''                    for (int oi = 0; oi < q.options.size(); oi++) {
                        if (q.options.get(oi).startsWith("-") && oi != q.answerIndex) negOpt++; // 负干扰项=缺陷
                    }
                    if (q.options.get(q.answerIndex).startsWith("-")) negAnswer++; // 负数答案（五六年级未学，P3）'''
assert old3 in src
src = src.replace(old3, new3)
src = src.replace('int mulBad = 0, mulTotal = 0, otherBad = 0, negOpt = 0, dupOpt = 0;',
                  'int mulBad = 0, mulTotal = 0, otherBad = 0, negOpt = 0, dupOpt = 0, negAnswer = 0;')
src = src.replace('check("T4.13d genMath 选项无负数", negOpt == 0, "neg=" + negOpt);',
                  'check("T4.13d genMath 无负数干扰项", negOpt == 0, "negDistractor=" + negOpt);\n'
                  '            System.out.println("INFO | T4.13e 五六年级混合运算负数答案出现 " + negAnswer + " 次（P3 设计问题，答案可为负但干扰项恒非负）");')

open(path, 'w', encoding='utf-8', newline='\n').write(src)
print('patched OK')
