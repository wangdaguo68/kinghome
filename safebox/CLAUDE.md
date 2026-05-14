# 保险箱 (SafeBox) - 文件加密保险箱

WPF .NET 10 桌面应用，使用 AES-256-GCM 分块加密存储文件。

## 技术栈
- WPF (.NET 10, C#) - 桌面 UI
- AES-256-GCM - 文件加密
- WiX v4 - MSI 安装包

## 项目结构
```
SafeBoxApp/          - WPF 应用代码
  MainWindow.xaml    - UI 布局
  MainWindow.xaml.cs - UI 逻辑 (~730行)
  VaultService.cs    - 加密/解密核心
installer/           - WiX 安装包
  Package.wxs        - 安装包定义
  installer.wixproj  - WiX 项目文件
dist/                - 发布输出 + 安装包
docs/                - 设计和计划文档
```

## 构建命令
```bash
# 自包含发布 (包含 .NET 运行时)
dotnet publish SafeBoxApp/SafeBoxApp.csproj -c Release -r win-x64 --self-contained true -o dist

# 构建 MSI 安装包
dotnet build installer/installer.wixproj -c Release
```

## 关键信息
- 输出文件: dist/保险箱.exe (自包含，无需安装 .NET 运行时)
- 安装包: dist/保险箱_安装包_v1.1.msi (67MB)
- 安装包有自定义选项页：桌面快捷方式 + 开机自启动 (默认勾选)
- 语言: 中文 (Language=2052, Codepage=936)
- WiX v4 语法: Control的Text用属性、CheckBox用CheckBoxValue、Component条件用Condition属性、HarvestDirectory自动采集文件

## 最新改动 (2026-05-14)
- 自包含发布，免 .NET 运行时依赖
- WiX HarvestDirectory 自动采集文件组件
- 安装包自定义选项页 (桌面快捷方式、开机自启)
- 异步文件操作 (预览、导入、导出不再卡 UI)
- 批量勾选 + 右键菜单 + 双击打开
- 导出后可选删除保险箱内文件

## Git 仓库
- GitHub: wangdaguo68/kinghome.git
- SSH 别名: origin (git@github-wangdaguo68:wangdaguo68/kinghome.git)
