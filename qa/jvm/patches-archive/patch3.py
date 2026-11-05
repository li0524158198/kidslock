# -*- coding: utf-8 -*-
"""按行号整体重写 T4.13 块"""
path = r'D:\project\kidslock\qa\jvm\src\JvmTests.java'
lines = open(path, encoding='utf-8').read().split('\n')

start = next(i for i, l in enumerate(lines) if 'T4.13 genMath' in l)
# 块尾：T4.13d 的 check 调用行（含续行）
end = next(i for i, l in enumerate(lines) if 'T4.13d' in l)
while ');' not in lines[end]:
    end += 1

MUL = chr(215)
block = [
'        // T4.13 genMath 隔离测试（反射调用私有方法，排除内置坏数据干扰）',
'        {',
'            java.lang.reflect.Method gen = QuestionBank.class.getDeclaredMethod("genMath", int.class);',
'            gen.setAccessible(true);',
'            int mulBad = 0, mulTotal = 0, otherBad = 0, negDistractor = 0, dupOpt = 0, negAnswer = 0;',
'            String mulSample = "", otherSample = "";',
'            java.util.regex.Pattern p3 = java.util.regex.Pattern.compile("([0-9]+) [+] ([0-9]+) - ([0-9]+) = [?]$");',
'            java.util.regex.Pattern pe = java.util.regex.Pattern.compile("解方程：([0-9]+)x [+] ([0-9]+) = ([0-9]+)，x = [?]$");',
'            java.util.regex.Pattern p2 = java.util.regex.Pattern.compile("([0-9]+) ([+ -]) ([0-9]+) = [?]$");',
'            for (int g = 1; g <= 9; g++) {',
'                for (int i = 0; i < 3000; i++) {',
'                    QuestionBank.Question q = (QuestionBank.Question) gen.invoke(qb, g);',
'                    if (q == null) { otherBad++; otherSample = "g" + g + " null"; continue; }',
'                    if (new HashSet<>(q.options).size() != 4) dupOpt++;',
'                    for (int oi = 0; oi < q.options.size(); oi++) {',
'                        if (q.options.get(oi).startsWith("-") && oi != q.answerIndex) negDistractor++;',
'                    }',
'                    if (q.options.get(q.answerIndex).startsWith("-")) negAnswer++;',
'                    long expect; java.util.regex.Matcher m;',
'                    if ((m = p3.matcher(q.text)).matches()) {',
'                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(2)) - Long.parseLong(m.group(3));',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }',
'                    } else if ((m = pe.matcher(q.text)).matches()) {',
'                        expect = (Long.parseLong(m.group(3)) - Long.parseLong(m.group(2))) / Long.parseLong(m.group(1));',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }',
'                    } else if (q.text.indexOf(MULCH) >= 0 && (m = mulPat.matcher(q.text)).matches()) {',
'                        expect = Long.parseLong(m.group(1)) * Long.parseLong(m.group(3));',
'                        mulTotal++;',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { mulBad++; if (mulSample.isEmpty()) mulSample = q.text + " marked=" + q.options.get(q.answerIndex) + " expect=" + expect; }',
'                    } else if ((m = divPat.matcher(q.text)).matches()) {',
'                        expect = Long.parseLong(m.group(1)) / Long.parseLong(m.group(3));',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }',
'                    } else if ((m = addPat.matcher(q.text)).matches()) {',
'                        expect = Long.parseLong(m.group(1)) + Long.parseLong(m.group(3));',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }',
'                    } else if ((m = subPat.matcher(q.text)).matches()) {',
'                        expect = Long.parseLong(m.group(1)) - Long.parseLong(m.group(3));',
'                        if (Long.parseLong(q.options.get(q.answerIndex)) != expect) { otherBad++; if (otherSample.isEmpty()) otherSample = q.text; }',
'                    } else { otherBad++; if (otherSample.isEmpty()) otherSample = "unparsed: " + q.text; }',
'                }',
'            }',
'            check("T4.13a genMath 加减除/混合/方程：答案=重算值", otherBad == 0, "bad=" + otherBad + "; " + otherSample);',
'            check("T4.13b genMath 乘法：答案=a*b（已知缺陷文档化）", mulBad == 0,',
'                    mulBad + "/" + mulTotal + " wrong; e.g. " + mulSample);',
'            check("T4.13c genMath 选项 4 个互异", dupOpt == 0, "dup=" + dupOpt);',
'            check("T4.13d genMath 无负数干扰项", negDistractor == 0, "negDistractor=" + negDistractor);',
'            System.out.println("INFO | T4.13e 五六年级负数答案出现 " + negAnswer + " 次（P3：答案可为负、干扰项恒非负，五六年级未学负数）");',
'        }',
]
# 需要的常量/Pattern 定义（插入块首）
block.insert(6, '            final char MULCH = ' + str(ord(MUL)) + '; // ' + MUL)
block.insert(7, '            java.util.regex.Pattern mulPat = java.util.regex.Pattern.compile("([0-9]+) [" + MULCH + "] ([0-9]+) = [?]$");')
block.insert(8, '            java.util.regex.Pattern divPat = java.util.regex.Pattern.compile("([0-9]+) [" + chr(247) + "] ([0-9]+) = [?]$");')
block.insert(9, '            java.util.regex.Pattern addPat = java.util.regex.Pattern.compile("([0-9]+) [+] ([0-9]+) = [?]$");')
block.insert(10, '            java.util.regex.Pattern subPat = java.util.regex.Pattern.compile("([0-9]+) [-] ([0-9]+) = [?]$");')
# 删除旧 p2/p3/pe 三行定义（在新块中不需要）
block = [l for l in block if 'Pattern p2 = ' not in l and 'Pattern p3 = ' not in l and 'Pattern pe = ' not in l]

lines[start:end+1] = block
open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('T4.13 block rewritten: lines', start, '-', end)
