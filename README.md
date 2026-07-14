# みんなのオンライン自習室 — Pythonプロトタイプ

通信制大学の学生が、顔出しや音声なしで「今、ほかの学生も一緒に学んでいる」と感じられるオンライン自習室です。

## 主な機能

- 匿名・ニックネームで入室
- 現在の科目、授業回、資格勉強などを表示
- 授業ページからの簡易参加リンク
- 退室時に今回の学習時間と科目別内訳を表示
- 同時参加人数をリアルタイム表示
- 10秒ごとの自動更新
- 意見・要望フォーム
- 管理者用の意見確認・CSVダウンロード
- 一定時間アクセスがない参加者の自動退室
- SQLiteによる簡易データ共有

## 動かし方

Python 3.11以上を推奨します。

Windows PowerShell:

```powershell
pip install -r requirements.txt
python -m streamlit run app.py
```

ブラウザで通常は `http://localhost:8501` が開きます。

同じPCで複数参加者を試す場合は、通常ブラウザとシークレットウィンドウを併用してください。

※ 仮想環境（venv）は必須ではありません。複数のPythonプロジェクトを使い分ける場合は、必要に応じて仮想環境を作成してください。

## 公開方法の考え方

このアプリはSQLiteに以下のデータを保存します。

- 現在の入室情報
- 意見・要望
- 入室、更新、退室、自動退室の履歴

そのため、公開先は「SQLiteファイルを消さずに保持できる環境」を選ぶのが安全です。

### 推奨：永続ディスク付きのホスティング

Render、Railway、VPS、学内サーバーなど、アプリ再起動後もファイルを保持できる環境が向いています。

起動コマンド例:

```bash
python -m streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

管理者画面は通常画面からリンクしません。
管理者パスワードを必ず設定してください。

### 手軽だが注意：Streamlit Community Cloud

Streamlit Community CloudはGitHubから簡単に公開できますが、ローカルファイル保存の永続性は保証されません。

そのため、SQLiteに保存した意見・要望や履歴を長期間保持したい場合は、Community Cloud単体での運用は避けるか、定期的にCSVをダウンロードしてください。

公開手順の概要:

1. GitHubリポジトリに `app.py`、`admin.py`、`requirements.txt`、`README.md` を置く
2. `study_room.db` や `.streamlit/secrets.toml` はGitHubに含めない
3. Streamlit Community Cloudでリポジトリを選択する
4. メインアプリは `app.py` をエントリーポイントにする
5. Secretsで管理者パスワードを設定する
6. 管理者画面のURLは公開READMEには記載しない

## 公開前のセキュリティ確認

- 本名、学籍番号、メールアドレスを入力しない運用にする
- 管理者パスワードは12文字以上の推測されにくい文字列にする
- `study_room.db`、`.streamlit/secrets.toml`、`.env` をGitHubにコミットしない
- 管理者画面は通常画面からリンクしない
- 管理者画面のURLは限定共有にする
- SQLiteは小規模プロトタイプ向け。本格運用ではPostgreSQLなどに移行する
- 意見・要望や利用履歴の保存目的、保存期間、削除方法を利用者に説明する

## 管理者向けメモ

送信された意見・要望はSQLiteの `feedback` テーブルに保存されます。

管理者画面は通常画面には表示されません。

ローカルで確認する場合は、Windows PowerShellで管理者用パスワードを環境変数に設定して起動します。

```powershell
$env:STUDY_ROOM_ADMIN_PASSWORD="任意のパスワード"
python -m streamlit run app.py
```

Streamlit Community Cloudで使う場合は、アプリのSecretsに管理者パスワードを設定します。

```toml
STUDY_ROOM_ADMIN_PASSWORD = "任意のパスワード"
```

管理者画面のURLは公開READMEには記載せず、運用者だけが別途管理してください。

管理者画面では以下を確認できます。

- 現在の入室者数
- 現在の部屋別人数
- 累計入室数（部屋別）
- 入室、更新、退室、自動退室の履歴
- 意見・要望の一覧
- 入退室履歴と意見・要望のCSVダウンロード

入退室履歴はSQLiteの `presence_events` テーブルに保存されます。

## 授業ページからの簡易参加リンク

授業回ごとのページから、StudyRoomの該当する部屋へ簡易参加できます。

URL形式:

```text
https://studyroom.streamlit.app/?quick=1&course=info-basic&lesson=1
```

簡易参加では、表示名や状態は固定されます。

- 表示名: 匿名学生さん
- コメント: 一緒に学習中
- 状態: 集中して学習中
- 体感難易度: ふつう
- 表示時間: 60分

通常参加と異なり、ブラウザを閉じても60分間は部屋に表示されます。60分経過後は自動退室扱いになります。

### courseコード対応表

| course | 表示される部屋名 |
| --- | --- |
| `free-room` | フリールーム |
| `info-basic` | 情報基礎A・B |
| `internet-tech` | インターネット技術Ⅰ・Ⅱ |
| `data-algorithms` | データ構造とアルゴリズムⅠ・Ⅱ |
| `programming` | 実践プログラミングⅠ・Ⅱ |
| `secure-programming` | 初級セキュアプログラミング |
| `seminar` | 基礎ゼミA・B |
| `certification` | 資格勉強 |
| `other` | フリールーム |

### lesson指定

`lesson=1` から `lesson=8` までを指定すると、それぞれ `第1回` から `第8回` として参加します。

```text
https://studyroom.streamlit.app/?quick=1&course=internet-tech&lesson=3
```

`lesson=other` を指定すると `その他` として参加します。

## 授業ページ用サムネイル画像

授業ページには、StudyRoomの利用状況を画像として埋め込めます。

画像には、対象の部屋に入室中の人数と、StudyRoom全体の入室人数が表示されます。

### サムネイル画像URL一覧

| 部屋名 | 画像URL |
| --- | --- |
| フリールーム | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/free-room.svg` |
| 情報基礎A・B | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/info-basic.svg` |
| インターネット技術Ⅰ・Ⅱ | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/internet-tech.svg` |
| データ構造とアルゴリズムⅠ・Ⅱ | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/data-algorithms.svg` |
| 実践プログラミングⅠ・Ⅱ | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/programming.svg` |
| 初級セキュアプログラミング | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/secure-programming.svg` |
| 基礎ゼミA・B | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/seminar.svg` |
| 資格勉強 | `https://studyroom-status.yosuke-tsuchiya.workers.dev/status/certification.svg` |

### 授業ページ貼り付け用HTML

フリールーム:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/free-room.svg" alt="StudyRoom Live Status - Free Room">
```

情報基礎A・B:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/info-basic.svg" alt="StudyRoom Live Status - Information Technology A/B">
```

インターネット技術Ⅰ・Ⅱ:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/internet-tech.svg" alt="StudyRoom Live Status - Internet Technology I/II">
```

データ構造とアルゴリズムⅠ・Ⅱ:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/data-algorithms.svg" alt="StudyRoom Live Status - Data Structures and Algorithms I/II">
```

実践プログラミングⅠ・Ⅱ:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/programming.svg" alt="StudyRoom Live Status - Practical Programming I/II">
```

初級セキュアプログラミング:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/secure-programming.svg" alt="StudyRoom Live Status - Secure Programming Basics">
```

基礎ゼミA・B:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/seminar.svg" alt="StudyRoom Live Status - Basic Seminar A/B">
```

資格勉強:

```html
<img src="https://studyroom-status.yosuke-tsuchiya.workers.dev/status/certification.svg" alt="StudyRoom Live Status - Certification Study">
```

### サムネイル画像運用メモ

- 入室、退室、学習内容の更新、自動退室処理のタイミングで画像が更新されます。
- 画像更新は非同期で実行されるため、StudyRoomの画面操作より少し遅れて反映される場合があります。
- サムネイル画像はCloudflare WorkerがSVGとして生成します。通常は入退室後すぐに反映されます。
- Cloudflare WorkerのURLを変更した場合は、Streamlit CloudのSecretsに設定している `STATUS_IMAGE_WEBHOOK_URL` も更新してください。
- Cloudflare Workerの認証トークンを変更した場合は、Streamlit CloudのSecretsに設定している `STATUS_IMAGE_WEBHOOK_TOKEN` も更新してください。

### @ROOMページ表示回数画像（検討中）

StudyRoomの入室状況画像とは別に、@ROOM側の授業ページが最近表示された回数を示す画像を追加する案があります。

URL形式:

```text
https://studyroom-status.yosuke-tsuchiya.workers.dev/views/info-basic/lesson-1.svg
```

この画像は、該当する授業回ページが表示された回数を、直近24時間と直近7日間で表示します。

```text
@ROOM ページ表示
情報基礎A・B 第1回
24時間 5回表示 / 7日間 32回表示
```

注意:

- 表示されるのは「人数」ではなく「画像の表示回数」です。
- 同じ学生がページを再読み込みした場合も回数に含まれます。
- StudyRoomに入室、チェックインした人数とは別の補助情報として扱います。
- 実装候補のCloudflare Workerコードは `cloudflare_worker_status.js` にあります。
- 授業ページ貼り付け用の `<img>` タグ一覧は `page_view_image_tags.md` にあります。

## プロトタイプの位置づけ

この版は授業導入前のユーザーテスト用です。SQLiteを使うため、単一サーバー・小人数での検証に向きます。

本番運用では、次の追加が必要です。

1. 大学アカウントによる認証。ただし画面上はニックネームのみ表示
2. PostgreSQLなどの共有データベース
3. 不適切投稿の通報、削除、ミュート、NGワード
4. 科目マスタと履修者権限
5. 管理者画面と利用状況の匿名集計
6. ログ保存期間とプライバシーポリシー
7. 質問や問い合わせへの導線
8. WebSocketまたはマネージドリアルタイム基盤による即時更新

## 研究・評価案

導入前後で以下を匿名アンケートにすると、効果を評価しやすくなります。

- 授業受講時に孤独を感じる
- 学習を始めるきっかけになった
- ほかの学生の存在が励みになった
- 科目名を公開することに抵抗がある
- 意見・要望フォームを使いやすいと感じた
- 今後も利用したい

5件法に加え、自由記述と利用ログの集計を組み合わせる設計が考えられます。

