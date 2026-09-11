# Smart Access & Reception System 🚀

*English | [日本語](#japanese)*

An enterprise-grade, edge-based Smart Access Control and Time Attendance system. Built with Python and OpenCV, it features a real-time web dashboard, interactive gamified attendance tracking, hardware integration, and a unique PS1-style retro particle animation.

## ✨ Features
* **Face Recognition**: Fast and accurate edge face detection using `dlib` and `face_recognition`.
* **Single Page Application (SPA)**: Real-time UI built with Flask & Socket.IO.
  * **Scanner View**: A stunning retro PS1-style particle engine that physically reassembles the user's face upon successful scan.
  * **Analytics Dashboard**: Live datatable pulling access logs directly from an SQLite database.
  * **Campus Map**: Gamified presence tracker. Avatars dynamically fly between "HOME" and "INSTITUTE" zones upon Entry/Exit.
* **Time & Attendance Tracking**: Automatically determines if a scan is an `ENTRY` or `EXIT` and logs the timestamp.
* **Hardware Integration (I2C/GPIO)**: Code is structured to support Relays (for turnstiles/magnetic locks) and MLX90614 Infrared Thermal Scanners (checks for fever before granting access).
* **Security Webhooks**: Detects unknown intruders (lingering > 3 seconds) and sends a snapshot alert via LINE Notify.
* **Voice Assistant (TTS)**: Greets users by name, role, and current time ("Welcome", "Goodbye").

## 🛠️ Tech Stack
* **Backend**: Python 3, Flask, Flask-SocketIO, Eventlet, SQLite
* **Computer Vision**: OpenCV (`cv2`), `face_recognition`
* **Frontend**: HTML5 Canvas, Vanilla JS, CSS3
* **Hardware**: Ready for Raspberry Pi GPIO & I2C

## 🚀 How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Add photos to the `database` folder. Naming format: `Name_Role.jpg` (e.g., `SolidSnake_Student.jpg`).
3. Run the server:
   ```bash
   python main.py
   ```
4. Open the web interface at `http://localhost:5000/`.

---

<a name="japanese"></a>
# Smart Access & Reception System 🚀 (スマート・アクセス＆受付システム)

エッジベースで動作するエンタープライズ向けのスマート入退室管理・勤怠追跡システムです。PythonとOpenCVで構築され、リアルタイムのWebダッシュボード、ゲーミフィケーション化された勤怠トラッキング、ハードウェア連携、そしてPS1風のレトロなパーティクルアニメーションを備えています。

## ✨ 主な機能
* **顔認識**: `dlib` と `face_recognition` を用いた高速かつ高精度なエッジ顔検出。
* **シングルページアプリケーション (SPA)**: Flask と Socket.IO で構築されたリアルタイムUI。
  * **スキャナー・ビュー**: 認証成功時、ユーザーの顔をPS1風のレトロなパーティクル（粒子）で物理的に再構築する美しいエフェクト。
  * **分析ダッシュボード**: SQLiteデータベースから入退室ログを直接取得し、リアルタイムで表示するデータテーブル。
  * **キャンパスマップ**: ゲーミフィケーション化された出欠トラッカー。入室・退室時にアバターが「HOME」と「INSTITUTE（施設）」ゾーン間をダイナミックに飛び交います。
* **勤怠トラッキング**: スキャンが「入室（ENTRY）」か「退室（EXIT）」かを自動的に判別し、タイムスタンプを記録。
* **ハードウェア統合 (I2C/GPIO)**: リレー（改札機や電磁錠用）およびMLX90614赤外線サーマルスキャナ（入室前に発熱をチェック）をサポートする構造。
* **セキュリティ Webhook**: 未知の侵入者（3秒以上滞在）を検知し、LINE Notify経由でスナップショット警告を送信。
* **音声アシスタント (TTS)**: ユーザーの名前、役職、現在時刻を音声で読み上げ挨拶（「Welcome」「Goodbye」等）。

## 🛠️ 技術スタック
* **バックエンド**: Python 3, Flask, Flask-SocketIO, Eventlet, SQLite
* **コンピュータービジョン**: OpenCV (`cv2`), `face_recognition`
* **フロントエンド**: HTML5 Canvas, Vanilla JS, CSS3
* **ハードウェア**: Raspberry Pi GPIO & I2C 対応設計

## 🚀 実行方法
1. 依存パッケージのインストール:
   ```bash
   pip install -r requirements.txt
   ```
2. `database` フォルダに写真を入れます。ファイル名の形式: `名前_役職.jpg` (例: `SolidSnake_Student.jpg`)。
3. サーバーを起動します:
   ```bash
   python main.py
   ```
4. ブラウザで `http://localhost:5000/` を開きます。
