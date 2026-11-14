# 소개팅 부스를 한 번에 받아서 켠다 (윈도우 PowerShell).
#
# PowerShell 창에 아래 한 줄을 붙여 넣고 Enter:
#
#   irm https://raw.githubusercontent.com/foggyjupiter/2026-LTE-ANN-project/refs/heads/main/booth.ps1 | iex
#
# 하는 일 (내 사용자 폴더의 sogaeting-booth 폴더 하나만 쓴다):
#   1. Python 3.10 이상이 없으면 winget 으로 설치한다.
#   2. 게임 코드(main 브랜치)를 받는다. 켤 때마다 새로 받는다. .env 와 results 는 남긴다.
#   3. Ren'Py SDK 8.5.3 이 없으면 받는다 (약 160MB, 처음 한 번만).
#   4. Gemini 키를 처음 한 번 묻고 sogaeting-booth\.env 에 적는다. 그냥 Enter 를 누르면 가짜 모델로 켠다.
#      키가 있으면 모델마다 짧게 불러 점검하고(python -m sogaeting.check), 답한 곳이 없으면 새 키를 묻는다.
#   5. python run_booth.py 로 서버와 게임을 켠다.
#
# 키를 다시 넣으려면 sogaeting-booth\.env 를 지우고 다시 실행한다.
# 키는 이 PC의 .env 에만 적힌다. 레포에는 올라가지 않는다.

& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'   # 진행 막대를 그리면 내려받기가 몇 배 느려진다

    $Repo = 'foggyjupiter/2026-LTE-ANN-project'
    $Branch = 'main'
    $SdkVersion = '8.5.3'
    $Base = Join-Path $HOME 'sogaeting-booth'
    $Game = Join-Path $Base 'game'
    $EnvFile = Join-Path $Base '.env'

    function Say($text) { Write-Host "[부스] $text" -ForegroundColor Cyan }

    function Get-File($url, $out) {
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            & curl.exe -L --fail --retry 3 -o $out $url
            if ($LASTEXITCODE -ne 0) { throw "내려받지 못했습니다: $url" }
        } else {
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $out
        }
    }

    function Expand-Zip($zip, $dest) {
        New-Item -ItemType Directory -Force $dest | Out-Null
        if (Get-Command tar.exe -ErrorAction SilentlyContinue) {
            & tar.exe -xf $zip -C $dest   # Expand-Archive 보다 훨씬 빠르다
            if ($LASTEXITCODE -eq 0) { return }
            Say 'tar 로 풀지 못해서 Expand-Archive 로 다시 풉니다. 조금 오래 걸립니다.'
        }
        Expand-Archive -Force -Path $zip -DestinationPath $dest
    }

    function Find-Python {
        $candidates = @(
            @('py', '-3'),
            @('python'),
            @("$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"),
            @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe")
        )
        foreach ($c in $candidates) {
            $exe = $c[0]
            if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
            $rest = @($c | Select-Object -Skip 1)
            try {
                $ok = & $exe @rest -c "import sys; print(sys.version_info >= (3, 10))" 2>$null
            } catch { continue }
            if ($ok -eq 'True') { return ,$c }
        }
        return $null
    }

    New-Item -ItemType Directory -Force $Base | Out-Null
    Say "작업 폴더: $Base"

    # 1. Python
    $py = Find-Python
    if (-not $py) {
        Say 'Python 3.10 이상이 없어서 설치합니다 (winget, 사용자 폴더에 설치).'
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw 'winget 이 없습니다. https://www.python.org/downloads/ 에서 Python 을 설치하고 (Add python.exe to PATH 체크) 다시 실행해 주세요.'
        }
        & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        $py = Find-Python
        if (-not $py) { throw 'Python 설치 뒤에도 찾지 못했습니다. PowerShell 창을 새로 열고 다시 실행해 주세요.' }
    }
    $pyExe = $py[0]
    $pyArgs = @($py | Select-Object -Skip 1)
    Say ("Python: " + (& $pyExe @pyArgs --version))

    # 2. 게임 코드 (켤 때마다 최신으로)
    Say "게임 코드를 받습니다 ($Branch)."
    $zip = Join-Path $Base 'code.zip'
    $fresh = Join-Path $Base 'fresh'
    if (Test-Path $fresh) { Remove-Item -Recurse -Force $fresh }
    Get-File "https://codeload.github.com/$Repo/zip/refs/heads/$Branch" $zip
    Expand-Zip $zip $fresh
    Remove-Item -Force $zip
    $inner = Get-ChildItem -Directory $fresh | Select-Object -First 1
    if (Test-Path $Game) {
        $keep = Join-Path $Game 'results'
        if (Test-Path $keep) { Copy-Item -Recurse -Force $keep (Join-Path $inner.FullName 'results') }
        Remove-Item -Recurse -Force $Game
    }
    Move-Item $inner.FullName $Game
    Remove-Item -Recurse -Force $fresh

    # 3. Ren'Py SDK (처음 한 번만). run_booth.py 가 게임 폴더 옆(sogaeting-booth)에서 알아서 찾는다
    function Find-Sdk {
        Get-ChildItem -Path $Base -Directory -Filter "renpy-$SdkVersion-sdk*" -ErrorAction SilentlyContinue |
            ForEach-Object { Get-ChildItem -Path $_.FullName -Filter renpy.exe -Recurse -Depth 1 -ErrorAction SilentlyContinue } |
            Select-Object -First 1
    }
    if (-not (Find-Sdk)) {
        Say "Ren'Py SDK $SdkVersion 를 받습니다. 약 160MB 라 몇 분 걸릴 수 있습니다."
        $sdkZip = Join-Path $Base 'renpy-sdk.zip'
        Get-File "https://www.renpy.org/dl/$SdkVersion/renpy-$SdkVersion-sdk.zip" $sdkZip
        Expand-Zip $sdkZip $Base
        Remove-Item -Force $sdkZip
        if (-not (Find-Sdk)) { throw "SDK 를 풀었는데 $Base 안에서 renpy.exe 를 찾지 못했습니다." }
    }
    Remove-Item Env:RENPY_SDK -ErrorAction SilentlyContinue   # 다른 곳을 가리키는 값이 있으면 그곳만 보므로 지운다

    # 4. 키
    function Read-Key($prompt) {
        Write-Host ''
        Write-Host $prompt
        Write-Host '예비 키는 쉼표로 이어 적습니다 (키1,키2). AI Studio에서 프로젝트를 새로 만들어 받은 키여야 한도가 따로 잡힙니다.'
        $secure = Read-Host -AsSecureString '키 (화면에는 안 보입니다)'
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim() }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    function Save-Key($key) {
        # BOM 없는 UTF-8 로 쓴다. 키가 비어 있으면 주석 한 줄만 남겨 다음부터 묻지 않는다
        $line = if ($key) { "GEMINI_API_KEY=$key" } else { '# GEMINI_API_KEY=' }
        [IO.File]::WriteAllText($EnvFile, $line + "`n")
        Copy-Item -Force $EnvFile (Join-Path $Game '.env')
    }
    if (-not (Test-Path $EnvFile)) {
        Save-Key (Read-Key 'Gemini API 키를 붙여 넣고 Enter 를 누르세요. 키 없이 가짜 모델로 켜려면 그냥 Enter.')
    }
    Copy-Item -Force $EnvFile (Join-Path $Game '.env')
    $hasKey = Select-String -Path $EnvFile -Pattern '^\s*GEMINI_API_KEY\s*=\s*\S' -Quiet
    Set-Location $Game

    if ($hasKey) {
        # 윈도우 환경변수에 예전 키가 있으면 .env 의 새 키가 무시된다. 이 창에서만 지운다
        foreach ($name in 'GEMINI_API_KEY', 'GROQ_API_KEY') {
            $inFile = Select-String -Path $EnvFile -Pattern "^\s*$name\s*=\s*\S" -Quiet
            if ($inFile -and (Test-Path "Env:$name")) {
                Say "윈도우 환경변수의 $name 대신 sogaeting-booth\.env 의 값을 씁니다."
                Remove-Item "Env:$name"
            }
        }
        Say '키를 점검합니다 (모델마다 짧게 한 번씩 부릅니다).'
        & $pyExe @pyArgs -m sogaeting.check
        if ($LASTEXITCODE -ne 0) {
            $new = Read-Key '답한 곳이 없습니다. 새 키를 붙여 넣으면 바꿔서 다시 점검합니다. 그대로 켜려면 그냥 Enter.'
            if ($new) {
                Save-Key $new
                & $pyExe @pyArgs -m sogaeting.check
            }
            $new = $null
        }
    }

    # 5. 켜기
    if ($hasKey) {
        Say '실제 모델로 켭니다. 게임 창을 닫으면 서버도 꺼집니다.'
        & $pyExe @pyArgs run_booth.py
    } else {
        Say '키가 없어서 가짜 모델로 켭니다. 키를 넣으려면 sogaeting-booth\.env 를 지우고 다시 실행하세요.'
        & $pyExe @pyArgs run_booth.py --fake
    }
}
