import { router, promptAction } from '@kit.ArkUI';
import { AppInit } from '../model/AppInit';

/**
 * 设置主界面。
 * 家长可以在这里配置：自动继续、观看时长、解锁题数、家长PIN码。
 * 还可以开始/停止计时、立即锁屏、查看剩余时间。
 */
@Entry
@Component
struct Index {
  @StorageLink('isLocked') isLocked: boolean = false;
  @StorageLink('timerActive') timerActive: boolean = false;
  @StorageLink('autoStart') autoStart: boolean = true;
  @StorageLink('watchLimitMinutes') watchLimitMinutes: number = 30;
  @StorageLink('unlockCount') unlockCount: number = 3;
  @StorageLink('parentPin') parentPin: string = '1234';

  @State remainingText: string = '';
  @State statusText: string = '当前状态：未计时';
  @State statusColor: ResourceColor = $r('app.color.text_secondary');
  private tickId: number = -1;

  private readonly timeOptions: number[] = [15, 30, 45, 60, 90, 120];
  private readonly countOptions: number[] = [3, 5, 10];

  aboutToAppear(): void {
    this.tick();
    this.tickId = setInterval(() => {
      this.tick();
    }, 1000);
  }

  aboutToDisappear(): void {
    if (this.tickId >= 0) {
      clearInterval(this.tickId);
    }
  }

  onPageShow(): void {
    // 如果当前处于锁屏状态，禁止进入设置页（防止从桌面图标绕过锁屏解锁）
    if (this.isLocked) {
      router.replaceUrl({ url: 'pages/Lock' });
    }
    this.tick();
  }

  private tick(): void {
    if (this.isLocked) {
      this.statusText = '当前状态：已锁屏';
      this.statusColor = $r('app.color.wrong_red');
      this.remainingText = '请答题解锁';
      return;
    }
    if (this.timerActive) {
      const remaining = AppInit.remainingMillis();
      if (remaining <= 0) {
        this.statusText = '当前状态：时间到';
        this.statusColor = $r('app.color.wrong_red');
        // 到时自动锁屏
        AppInit.stopTimer();
        this.isLocked = true;
        router.replaceUrl({ url: 'pages/Lock' });
        return;
      }
      this.statusText = '当前状态：计时中';
      this.statusColor = $r('app.color.correct_green');
      const totalSec = Math.floor(remaining / 1000);
      const min = Math.floor(totalSec / 60);
      const sec = totalSec % 60;
      this.remainingText = `剩余时间：${this.pad(min)}:${this.pad(sec)}`;
    } else {
      this.statusText = '当前状态：未计时';
      this.statusColor = $r('app.color.text_secondary');
      this.remainingText = '';
    }
  }

  private pad(n: number): string {
    return n < 10 ? `0${n}` : `${n}`;
  }

  private toast(msg: string): void {
    promptAction.showToast({ message: msg, duration: 2000 });
  }

  build() {
    Stack() {
      Column() {
      // 标题栏
      Text('儿童锁屏设置')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .fontColor($r('app.color.accent'))
        .width('100%')
        .textAlign(TextAlign.Center)
        .padding(16)

      Scroll() {
        Column({ space: 12 }) {
          // 状态卡片
          Column({ space: 8 }) {
            Text(this.statusText)
              .fontSize(18)
              .fontWeight(FontWeight.Medium)
              .fontColor(this.statusColor)
            Text(this.remainingText)
              .fontSize(18)
              .fontColor($r('app.color.accent'))
              .fontFamily('monospace')
          }
          .width('100%')
          .padding(16)
          .borderRadius(12)
          .backgroundColor($r('app.color.bg_surface'))
          .alignItems(HorizontalAlign.Center)

          // 参数配置卡片
          Column({ space: 14 }) {
            Text('参数配置')
              .fontSize(16)
              .fontWeight(FontWeight.Bold)
              .fontColor($r('app.color.highlight'))
              .alignSelf(ItemAlign.Start)

            // 自动继续（原 Android 版「开机自启」）
            Row() {
              Text(this.autoStart ? '自动继续：已开启' : '自动继续：已关闭')
                .fontSize(16)
                .fontColor($r('app.color.text_primary'))
              Blank()
              Toggle({ type: ToggleType.Switch, isOn: this.autoStart })
                .onChange((isOn: boolean) => {
                  this.autoStart = isOn;
                  this.toast(isOn ? '已开启自动继续' : '已关闭自动继续');
                })
                .selectedColor($r('app.color.highlight'))
            }
            .width('100%')

            Divider().color($r('app.color.highlight')).opacity(0.3)

            // 观看时长
            Column({ space: 8 }) {
              Text(`观看时长：${this.watchLimitMinutes} 分钟`)
                .fontSize(16)
                .fontColor($r('app.color.text_primary'))
                .alignSelf(ItemAlign.Start)
              Row({ space: 8 }) {
                ForEach(this.timeOptions, (minutes: number) => {
                  Button(`${minutes}`)
                    .fontSize(15)
                    .fontColor(this.watchLimitMinutes === minutes ? $r('app.color.bg_dark') : $r('app.color.text_primary'))
                    .backgroundColor(this.watchLimitMinutes === minutes ? $r('app.color.highlight') : $r('app.color.bg_surface_light'))
                    .layoutWeight(1)
                    .onClick(() => {
                      this.watchLimitMinutes = minutes;
                      this.toast(`观看时长设为 ${minutes} 分钟`);
                    })
                }, (minutes: number) => minutes.toString())
              }
              .width('100%')
            }

            Divider().color($r('app.color.highlight')).opacity(0.3)

            // 解锁题数
            Column({ space: 8 }) {
              Text(`解锁题数：${this.unlockCount} 道连续答对`)
                .fontSize(16)
                .fontColor($r('app.color.text_primary'))
                .alignSelf(ItemAlign.Start)
              Row({ space: 8 }) {
                ForEach(this.countOptions, (count: number) => {
                  Button(`${count}`)
                    .fontSize(15)
                    .fontColor(this.unlockCount === count ? $r('app.color.bg_dark') : $r('app.color.text_primary'))
                    .backgroundColor(this.unlockCount === count ? $r('app.color.highlight') : $r('app.color.bg_surface_light'))
                    .layoutWeight(1)
                    .onClick(() => {
                      this.unlockCount = count;
                      this.toast(`解锁题数设为 ${count} 题`);
                    })
                }, (count: number) => count.toString())
              }
              .width('100%')
            }

            Divider().color($r('app.color.highlight')).opacity(0.3)

            // 设置PIN
            Button('设置家长PIN')
              .fontSize(16)
              .fontColor($r('app.color.accent'))
              .backgroundColor($r('app.color.primary'))
              .width('100%')
              .onClick(() => {
                this.pinInput = '';
                this.pinDialogVisible = true;
              })
          }
          .width('100%')
          .padding(16)
          .borderRadius(12)
          .backgroundColor($r('app.color.bg_surface'))
          .alignItems(HorizontalAlign.Start)

          // 计时控制卡片
          Column({ space: 14 }) {
            Text('计时控制')
              .fontSize(16)
              .fontWeight(FontWeight.Bold)
              .fontColor($r('app.color.highlight'))
              .alignSelf(ItemAlign.Start)

            Button(this.timerActive ? '重新开始计时' : '开始计时')
              .fontSize(17)
              .fontWeight(FontWeight.Medium)
              .fontColor(Color.White)
              .backgroundColor($r('app.color.correct_green'))
              .width('100%')
              .onClick(() => {
                AppInit.startTimer(this.watchLimitMinutes);
                this.toast(`计时开始：${this.watchLimitMinutes} 分钟后锁屏`);
                this.tick();
              })

            Button('停止计时')
              .fontSize(16)
              .fontColor($r('app.color.accent'))
              .backgroundColor($r('app.color.primary'))
              .width('100%')
              .onClick(() => {
                AppInit.stopTimer();
                this.toast('计时已停止');
                this.tick();
              })

            Button('立即锁屏')
              .fontSize(16)
              .fontColor(Color.White)
              .backgroundColor($r('app.color.wrong_red'))
              .width('100%')
              .onClick(() => {
                AppInit.stopTimer();
                this.isLocked = true;
                router.replaceUrl({ url: 'pages/Lock' });
              })
          }
          .width('100%')
          .padding(16)
          .borderRadius(12)
          .backgroundColor($r('app.color.bg_surface'))
          .alignItems(HorizontalAlign.Start)
        }
        .padding(16)
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off)
      .width('100%')
    }
      .width('100%')
      .height('100%')
      .backgroundColor($r('app.color.bg_dark'))

      // PIN 设置弹窗遮罩
      this.pinDialogOverlay()
    }
    .width('100%')
    .height('100%')
    .expandSafeArea([SafeAreaType.SYSTEM], [SafeAreaEdge.TOP, SafeAreaEdge.BOTTOM])
  }

  // 使用简单的状态变量实现 PIN 输入（页面内遮罩弹窗）
  @State pinDialogVisible: boolean = false;
  @State pinInput: string = '';

  @Builder
  pinDialogOverlay() {
    if (this.pinDialogVisible) {
      Column() {
        Column({ space: 16 }) {
          Text('设置家长PIN码（4位数字）')
            .fontSize(17)
            .fontColor($r('app.color.text_primary'))
          TextInput({ placeholder: `当前PIN：${this.parentPin}`, text: this.pinInput })
            .type(InputType.Number)
            .maxLength(4)
            .width('100%')
            .onChange((value: string) => {
              this.pinInput = value;
            })
          Row({ space: 12 }) {
            Button('取消')
              .fontSize(15)
              .fontColor($r('app.color.text_secondary'))
              .backgroundColor($r('app.color.bg_surface_light'))
              .layoutWeight(1)
              .onClick(() => {
                this.pinDialogVisible = false;
              })
            Button('确定')
              .fontSize(15)
              .fontColor($r('app.color.accent'))
              .backgroundColor($r('app.color.primary'))
              .layoutWeight(1)
              .onClick(() => {
                if (this.pinInput.length === 4) {
                  this.parentPin = this.pinInput;
                  this.toast('PIN码已设置');
                } else {
                  this.toast('PIN码必须是4位数字');
                }
                this.pinDialogVisible = false;
              })
          }
          .width('100%')
        }
        .padding(20)
        .backgroundColor($r('app.color.bg_surface'))
        .borderRadius(12)
        .width('85%')
      }
      .width('100%')
      .height('100%')
      .backgroundColor('rgba(0,0,0,0.6)')
      .justifyContent(FlexAlign.Center)
    }
  }
}
