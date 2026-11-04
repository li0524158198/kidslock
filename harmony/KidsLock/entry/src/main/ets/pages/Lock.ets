import { router } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { AppInit } from '../model/AppInit';
import { QuestionBank, Question } from '../model/QuestionBank';

/**
 * 锁屏界面：按所选题库（人教版语数英）出题，连续答对指定题数解锁。
 * - 返回键无效（onBackPress 拦截）
 * - 答错重置计数
 * - 家长可通过输入 PIN 码强制解锁
 */
@Entry
@Component
struct Lock {
  @StorageLink('isLocked') isLocked: boolean = false;
  @StorageLink('unlockCount') unlockCount: number = 3;

  // 题目状态
  private qb: QuestionBank = new QuestionBank(getContext(this) as common.UIAbilityContext);
  @State bankLabel: string = '';
  @State questionText: string = '';
  @State bigChar: string | null = null;
  @State currentOptions: string[] = ['', '', '', ''];
  @State correctIndex: number = 0;
  @State correctCount: number = 0;
  @State answerLocked: boolean = false;
  @State selectedIndex: number = -1;
  @State wasCorrect: boolean = false;
  @State feedbackShown: boolean = false;

  // PIN 界面
  @State showPinPad: boolean = false;
  @State pinInput: string = '';
  @State pinMessage: string = '';
  @State pinMessageColor: ResourceColor = $r('app.color.wrong_red');

  aboutToAppear(): void {
    this.loadNextQuestion();
  }

  onPageShow(): void {
    // 如果已被解锁（例如从设置页解锁），回到设置页
    if (!this.isLocked) {
      router.replaceUrl({ url: 'pages/Index' });
    }
  }

  /** 屏蔽返回键，不允许退出锁屏 */
  onBackPress(): boolean {
    // 在PIN界面按返回 → 回到认字界面；否则返回键无效
    if (this.showPinPad) {
      this.showPinPad = false;
      this.pinInput = '';
      this.pinMessage = '';
    }
    return true;
  }

  // ==================== 出题（按所选题库） ====================

  private loadNextQuestion(): void {
    const bankId: string = AppStorage.get<string>('bankId') ?? 'chinese_primary';
    this.bankLabel = this.qb.getLabel(bankId);
    const q: Question = this.qb.getQuestion(bankId);
    this.questionText = q.text;
    this.bigChar = q.bigChar;
    this.currentOptions = q.options;
    this.correctIndex = q.answerIndex;
    this.selectedIndex = -1;
    this.answerLocked = false;
    this.feedbackShown = false;
  }

  private onOptionSelected(index: number): void {
    if (this.answerLocked || index >= this.currentOptions.length) {
      return;
    }
    this.answerLocked = true;
    this.selectedIndex = index;
    const selected = this.currentOptions[index];

    if (index === this.correctIndex) {
      // 答对了
      this.wasCorrect = true;
      this.feedbackShown = true;
      this.correctCount++;
      if (this.correctCount >= this.unlockCount) {
        // 全部答对，解锁
        setTimeout(() => {
          this.unlock();
        }, 600);
      } else {
        setTimeout(() => {
          this.loadNextQuestion();
        }, 1000);
      }
    } else {
      // 答错了
      this.wasCorrect = false;
      this.feedbackShown = true;
      this.correctCount = 0;
      setTimeout(() => {
        this.loadNextQuestion();
      }, 1500);
    }
  }

  private optionBg(index: number): ResourceColor {
    if (!this.answerLocked || this.selectedIndex < 0) {
      return $r('app.color.bg_surface');
    }
    if (index === this.selectedIndex) {
      return this.wasCorrect ? $r('app.color.correct_green') : $r('app.color.wrong_red');
    }
    if (!this.wasCorrect && index === this.correctIndex) {
      return $r('app.color.correct_green');
    }
    return $r('app.color.bg_surface');
  }

  private optionTextColor(index: number): ResourceColor {
    if (!this.answerLocked || this.selectedIndex < 0) {
      return $r('app.color.text_primary');
    }
    if (index === this.selectedIndex || (!this.wasCorrect && index === this.correctIndex)) {
      return Color.White;
    }
    return $r('app.color.text_secondary');
  }

  // ==================== 解锁 ====================

  private unlock(): void {
    AppInit.unlockAll();
    this.isLocked = false;
    router.replaceUrl({ url: 'pages/Index' });
  }

  // ==================== 家长PIN ====================

  private onPinDigit(digit: number): void {
    if (this.pinInput.length < 4) {
      this.pinInput += digit.toString();
      if (this.pinInput.length === 4) {
        setTimeout(() => {
          this.checkPin();
        }, 200);
      }
    }
  }

  private pinDot(i: number): string {
    return i < this.pinInput.length ? '●' : '○';
  }

  private checkPin(): void {
    const pin = AppStorage.get<string>('parentPin') ?? '1234';
    if (AppInit.isPinLocked()) {
      const remainingSec = Math.ceil(AppInit.pinLockRemainingMillis() / 1000);
      this.pinMessage = `尝试次数过多，请 ${remainingSec} 秒后再试`;
      this.pinMessageColor = $r('app.color.warning_orange');
      this.pinInput = '';
      return;
    }
    if (this.pinInput === pin) {
      AppInit.resetPinFailures();
      this.unlock();
    } else {
      AppInit.recordPinFailure();
      this.pinMessage = 'PIN码错误';
      this.pinMessageColor = $r('app.color.wrong_red');
      this.pinInput = '';
    }
  }

  build() {
    Column() {
      if (this.showPinPad) {
        this.pinPadView()
      } else {
        this.quizView()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor($r('app.color.bg_dark'))
    .expandSafeArea([SafeAreaType.SYSTEM], [SafeAreaEdge.TOP, SafeAreaEdge.BOTTOM])
  }

  @Builder
  quizView() {
    Column({ space: 10 }) {
      Text('屏幕已锁定')
        .fontSize(16)
        .fontColor($r('app.color.text_secondary'))
        .margin({ top: 16 })

      Text(this.bankLabel)
        .fontSize(14)
        .fontColor($r('app.color.highlight'))
        .margin({ top: 4 })

      if (this.bigChar !== null) {
        Text(this.bigChar)
          .fontSize(120)
          .fontWeight(FontWeight.Bold)
          .fontColor($r('app.color.accent'))
          .margin({ top: 8, bottom: 8 })
      }

      Text(this.questionText)
        .fontSize(18)
        .maxFontSize(32)
        .minFontSize(14)
        .height(72)
        .textAlign(TextAlign.Center)
        .fontColor($r('app.color.text_primary'))
        .width('92%')
        .margin({ top: 6 })

      Text(`已答对 ${this.correctCount}/${this.unlockCount} 道题即可解锁`)
        .fontSize(14)
        .fontColor($r('app.color.text_secondary'))

      // 反馈
      Text(this.wasCorrect ? '答对了！' : '答错了，重新开始！')
        .fontSize(16)
        .fontWeight(FontWeight.Medium)
        .fontColor(this.wasCorrect ? $r('app.color.correct_green') : $r('app.color.wrong_red'))
        .visibility(this.feedbackShown ? Visibility.Visible : Visibility.Hidden)
        .height(24)

      // 4个选项 2x2
      Grid() {
        ForEach(this.currentOptions, (option: string, index?: number) => {
          GridItem() {
            Button(option)
              .fontSize(20)
              .fontWeight(FontWeight.Medium)
              .fontColor(this.optionTextColor(index ?? 0))
              .backgroundColor(this.optionBg(index ?? 0))
              .width('100%')
              .height(56)
              .borderRadius(10)
              .onClick(() => {
                this.onOptionSelected(index ?? 0);
              })
          }
        }, (option: string) => option)
      }
      .columnsTemplate('1fr 1fr')
      .rowsGap(10)
      .columnsGap(10)
      .width('100%')
      .padding({ left: 24, right: 24 })

      // 家长解锁
      Button('家长解锁')
        .fontSize(14)
        .fontColor($r('app.color.highlight'))
        .backgroundColor(Color.Transparent)
        .margin({ top: 12, bottom: 16 })
        .onClick(() => {
          this.showPinPad = true;
          this.pinInput = '';
          this.pinMessage = '';
        })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Start)
    .alignItems(HorizontalAlign.Center)
  }

  @Builder
  pinPadView() {
    Column({ space: 16 }) {
      Text('请输入家长PIN码')
        .fontSize(17)
        .fontColor($r('app.color.text_secondary'))
        .margin({ top: 40 })

      Text(`${this.pinDot(0)}  ${this.pinDot(1)}  ${this.pinDot(2)}  ${this.pinDot(3)}`)
        .fontSize(24)
        .fontColor($r('app.color.accent'))

      Text(this.pinMessage)
        .fontSize(14)
        .fontColor(this.pinMessageColor)
        .height(20)

      Grid() {
        ForEach([1, 2, 3, 4, 5, 6, 7, 8, 9], (digit: number) => {
          GridItem() {
            Button(digit.toString())
              .fontSize(20)
              .fontColor($r('app.color.text_primary'))
              .backgroundColor($r('app.color.bg_surface'))
              .width('100%')
              .height(48)
              .borderRadius(10)
              .onClick(() => {
                this.onPinDigit(digit);
              })
          }
        }, (digit: number) => `d${digit}`)
        GridItem() {
          Button('清除')
            .fontSize(16)
            .fontColor($r('app.color.text_primary'))
            .backgroundColor($r('app.color.bg_surface'))
            .width('100%')
            .height(48)
            .borderRadius(10)
            .onClick(() => {
              this.pinInput = '';
            })
        }
        GridItem() {
          Button('0')
            .fontSize(20)
            .fontColor($r('app.color.text_primary'))
            .backgroundColor($r('app.color.bg_surface'))
            .width('100%')
            .height(48)
            .borderRadius(10)
            .onClick(() => {
              this.onPinDigit(0);
            })
        }
        GridItem() {
          Button('返回')
            .fontSize(16)
            .fontColor($r('app.color.highlight'))
            .backgroundColor($r('app.color.bg_surface'))
            .width('100%')
            .height(48)
            .borderRadius(10)
            .onClick(() => {
              this.showPinPad = false;
              this.pinInput = '';
              this.pinMessage = '';
            })
        }
      }
      .columnsTemplate('1fr 1fr 1fr')
      .rowsGap(12)
      .columnsGap(12)
      .width('80%')
    }
    .width('100%')
    .height('100%')
    .alignItems(HorizontalAlign.Center)
  }
}
