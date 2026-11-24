; DubEval's additions to electron-builder's installer (it includes build/installer.nsh by itself).
;
; An update (Restart to update runs the new installer with --updated) used to stop twice for a click: on the "who
; is this program for" page and on the Finish page. Both answers are already known, so an update now shows only the
; progress bar and starts DubEval when it's done. A first install still asks both, as before.

; The "who is this program for" page: an update keeps the way DubEval is installed now, without asking.
!macro customInstallMode
  ${if} ${isUpdated}
    ${if} $hasPerMachineInstallation == "1"
      StrCpy $isForceMachineInstall "1"
    ${else}
      StrCpy $isForceCurrentInstall "1"
    ${endif}
  ${endif}
!macroend

; The Finish page, as electron-builder draws it (with "Run DubEval"), except that an update skips it and starts
; DubEval at once.
!macro customFinishPage
  Function StartApp
    ${if} ${isUpdated}
      StrCpy $1 "--updated"
    ${else}
      StrCpy $1 ""
    ${endif}
    ${StdUtils.ExecShellAsUser} $0 "$launchLink" "open" "$1"
  FunctionEnd

  Function SkipFinishWhenUpdated
    ${if} ${isUpdated}
      Call StartApp
      Abort
    ${endif}
  FunctionEnd

  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_FUNCTION "StartApp"
  !define MUI_PAGE_CUSTOMFUNCTION_PRE SkipFinishWhenUpdated
  !insertmacro MUI_PAGE_FINISH
!macroend
