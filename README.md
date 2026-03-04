<h1 align="center">
  按键宏 - key macro
</h1>

核心库 keyboard、mouse，使用ctypes加载windows系统的user32.dll来监听键盘鼠标输入事件

提供了事件监听录制、播放，各录制脚本绑定快捷键，手动编辑事件代码

```
mouse left: down      鼠标左键按下
0106                  延迟时间106毫秒
mouse left: up        鼠标左键释放

space: down           空格键按下
0050                  延迟时间50毫秒
space: up             空格释放
```

使用pyside6 进行了高dpi 缩放兼容，使用 [qfluentwidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 进行前端美化

<img width="1046" height="409" alt="图片" src="https://github.com/user-attachments/assets/c94c898a-b08c-4218-b782-64143cc8919e" />
