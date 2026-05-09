# ドキュメント処理システム

スキャンされたドキュメントのOCRテキスト抽出・翻訳と、複数の画像/PDFを1つのPDFにまとめる機能を提供するWebアプリケーションです。

**FastAPI**（バックエンド）と **Streamlit**（フロントエンド）で構築し、**Google Cloud Vision API** と **Google Cloud Translation API** を活用しています。

---

## 機能

### OCR & 翻訳
- 画像（JPG/PNG）またはPDFをアップロード
- Cloud Translation API が対応する任意の言語ペアを選択
- Google Cloud Vision API でテキストを抽出
  - デジタルPDF：高速な直接抽出
  - スキャンPDF / 画像：Vision API による OCR
- 翻訳前に抽出テキストを手動編集可能
- Google Cloud Translation API で翻訳
- 翻訳結果を `.txt` ファイルでダウンロード

### PDFコンパイラ
- 複数の画像（JPG/PNG）やPDFをアップロード
- アップロード順にA4サイズの1つのPDFに結合
- 結合済みPDFをダウンロード

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| バックエンド | Python 3.10、FastAPI、Uvicorn |
| フロントエンド | Python 3.10、Streamlit |
| OCR | Google Cloud Vision API |
| 翻訳 | Google Cloud Translation API v3 |
| PDF処理 | PyMuPDF (fitz) |
| 画像処理 | Pillow |
| コンテナ | Docker、Docker Compose |

---

## 前提条件

- [Docker](https://docs.docker.com/get-docker/) および Docker Compose がインストール済みであること
- Google Cloud Platform アカウントがあること
- 請求が有効化された GCP プロジェクトがあること

---

## GCP の設定

### 1. GCP プロジェクトの作成または選択

[Google Cloud Console](https://console.cloud.google.com/) にアクセスし、新しいプロジェクトを作成するか、既存のプロジェクトを選択します。**プロジェクト ID** をメモしておいてください。

### 2. 必要な API の有効化

Cloud Console で **APIs & Services → ライブラリ** に移動し、以下の2つを有効化します。

- **Cloud Vision API**
- **Cloud Translation API**

`gcloud` コマンドを使う場合：

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable vision.googleapis.com translate.googleapis.com
```

### 3. サービスアカウントの作成

1. **IAM と管理 → サービスアカウント** に移動
2. **サービスアカウントを作成** をクリック
3. 任意の名前（例：`docs-helper-sa`）を入力し、**作成して続行** をクリック
4. 以下のロールを付与：
   - **編集者**（個人利用では最もシンプル）
   - 最小権限にする場合：**Cloud Translation API ユーザー**（`roles/cloudtranslate.user`）を付与。Cloud Vision API には専用のユーザーロールがないため、同一プロジェクト内のサービスアカウントは API を有効化するだけで利用可能
5. **完了** をクリック

### 4. サービスアカウントキーのダウンロード

1. 作成したサービスアカウントをクリック
2. **キー** タブを開く
3. **鍵を追加 → 新しい鍵を作成** をクリック
4. **JSON** を選択して **作成** をクリック
5. ダウンロードされた JSON ファイルを保存します。次のステップで `credentials/gcp-key.json` として配置します

---

## ローカル環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/YOUR_USERNAME/docs_helper.git
cd docs_helper
```

### 2. サービスアカウントキーの配置

`credentials/` ディレクトリを作成し、ダウンロードした JSON キーをコピーします。

```bash
mkdir credentials
cp /path/to/downloaded-key.json credentials/gcp-key.json
```

> `credentials/` は `.gitignore` に登録されており、コミットされることはありません。

### 3. `.env` ファイルの作成

サンプルをコピーしてプロジェクト ID を設定します。

```bash
cp .env.example .env
```

`.env` を編集：

```env
GCP_PROJECT_ID=your-gcp-project-id
```

`your-gcp-project-id` の部分を、手順1でメモした **プロジェクト ID**（例：`my-project-123`）に書き換えてください。

---

## Docker Compose での起動

```bash
docker-compose up --build
```

初回ビルド時は Python ベースイメージのダウンロードと依存パッケージのインストールが行われるため、数分かかります。

バックグラウンドで起動する場合：

```bash
docker-compose up --build -d
```

停止する場合：

```bash
docker-compose down
```

---

## アプリへのアクセス

| サービス | URL |
|---|---|
| Streamlit フロントエンド | http://localhost:8501 |
| FastAPI バックエンド（APIドキュメント） | http://localhost:8000/docs |

---

## ディレクトリ構成

```
docs_helper/
├── backend/
│   ├── main.py            # FastAPI アプリ（OCR・翻訳・PDF エンドポイント）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py             # ホームページ
│   ├── pages/
│   │   ├── 1_OCR翻訳.py        # OCR & 翻訳ページ
│   │   └── 2_PDFコンパイラ.py  # PDF コンパイラページ
│   ├── requirements.txt
│   └── Dockerfile
├── credentials/           # gcp-key.json をここに配置（gitignore 対象）
├── .env                   # ローカル環境変数（gitignore 対象）
├── .env.example
└── docker-compose.yml
```

---

## 環境変数

| 変数名 | 説明 | 例 |
|---|---|---|
| `GCP_PROJECT_ID` | GCP プロジェクト ID | `my-project-123` |
| `GOOGLE_APPLICATION_CREDENTIALS` | サービスアカウントキーのパス（Docker Compose が自動設定） | `/credentials/gcp-key.json` |
| `BACKEND_URL` | フロントエンドが使用するバックエンドの URL（Docker Compose が自動設定） | `http://backend:8000` |
