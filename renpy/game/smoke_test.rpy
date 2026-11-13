label smoke:
    $ smoke_cards = renpy.fetch(sg_server_url + "/api/characters", result="json", timeout=10)
    $ smoke_names = ", ".join(c["name"] for c in smoke_cards)
    "한글 시험: [smoke_names] 뷁 쀍 햏 똠방각하 ■■ → ±0 ♥"
    return

testcase smoke:
    run Jump("smoke")
    pause 1.5
    screenshot "smoke.png"
    exit
