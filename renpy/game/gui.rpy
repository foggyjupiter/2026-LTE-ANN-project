################################################################################
## 초기화
################################################################################

## 이 파일의 초기화 문이 다른 파일보다 먼저 실행되게 한다.
init offset = -2

## 화면 크기를 정하고 스타일을 기본값으로 되돌린다.
init python:
    gui.init(1280, 720)

## 화면이나 트랜스폼에서 서로 부딪히는 속성을 검사한다.
define config.check_conflicting_properties = True


################################################################################
## 글꼴과 색
################################################################################
##
## 소개팅 화면(sg_screens.rpy)이 쓰는 값이다. Ren'Py 기본 메뉴는 쓰지 않으므로
## 기본 GUI의 나머지 변수는 두지 않았다.

## 글꼴. 한글 11,172자가 모두 들어 있다.
define gui.text_font = "fonts/Pretendard-Regular.otf"
define gui.name_text_font = "fonts/Pretendard-Bold.otf"
define gui.interface_text_font = "fonts/Pretendard-Medium.otf"

## 글자 크기.
define gui.text_size = 26
define gui.name_text_size = 24
define gui.interface_text_size = 20

## 줄바꿈 규칙.
define gui.language = "unicode"

## 색. 화면 전체가 이 몇 가지만 쓴다.
define gui.sg_ink = "#171b36"          # 어두운 바탕과 밝은 바탕 위의 글자
define gui.sg_ink_soft = "#5a6288"     # 밝은 바탕 위의 흐린 글자
define gui.sg_paper = "#f7f8ff"        # 어두운 바탕 위의 글자
define gui.sg_paper_soft = "#c9cee8"   # 어두운 바탕 위의 흐린 글자
define gui.sg_pink = "#ff5c8a"         # 호감도
define gui.sg_blue = "#4d9cff"         # 호감도가 내려갈 때
define gui.sg_yellow = "#ffe14d"       # 형광펜, 알림
define gui.sg_violet = "#b48cff"       # NaN
