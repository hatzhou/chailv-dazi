; 差旅搭子 - Windows NSIS 安装包脚本
; 用法（需安装 NSIS：https://nsis.sourceforge.io）：
;   makensis scripts\installer.nsi
; 产物：dist\差旅搭子_Setup_v1.0.0.exe

!define APP_NAME "差旅搭子"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "差旅搭子团队"
!define APP_EXE "差旅搭子.exe"
!define APP_REGKEY "Software\差旅搭子"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "dist\${APP_NAME}_Setup_v${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\${APP_NAME}"
InstallDirRegKey HKCU "${APP_REGKEY}" "InstallDir"
RequestExecutionLevel user
ShowInstDetails show

Page directory
Page instfiles

Section "主程序" SecCore
    SectionIn RO
    SetOutPath "$INSTDIR"
    ; 将 dist\差旅搭子\ 目录下所有文件复制到安装目录
    File /r "dist\差旅搭子\*.*"

    ; 注册
    WriteRegStr HKCU "${APP_REGKEY}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "${APP_REGKEY}" "Version" "${APP_VERSION}"

    ; 开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\卸载${APP_NAME}.lnk" \
        "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0

    ; 桌面快捷方式
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    ; 卸载程序
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\卸载${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    DeleteRegKey HKCU "${APP_REGKEY}"
SectionEnd
