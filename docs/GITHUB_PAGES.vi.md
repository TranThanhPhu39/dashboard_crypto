**Dashboard miễn phí trên GitHub Pages**

Địa chỉ dashboard:

- Dashboard: https://tranthanhphu39.github.io/dashboard_crypto/dashboard/
- Metadata bản xuất: https://tranthanhphu39.github.io/dashboard_crypto/build_info.json

**Cách cập nhật**

Workflow `.github/workflows/pages.yml` kiểm tra bản xuất khi có pull request vào `main`. Sau khi push/merge `main` hoặc tới lịch, `.github/workflows/worker.yml` khôi phục checkpoint mã hóa, vận hành engine đã khóa, xác minh dữ liệu/giao diện, lưu checkpoint rồi xuất dashboard lên Pages. PR chỉ kiểm tra, không nhận secret hoặc deploy.

Theo dõi tại https://github.com/TranThanhPhu39/dashboard_crypto/actions . Chạy thủ công bằng `Actions -> Scheduled crypto worker and Pages -> Run workflow`, chọn `main` và `run` hoặc `monitor`.

Trong `Settings -> Pages`, nguồn xuất bản dùng `GitHub Actions`. Dashboard sử dụng các đường dẫn tương đối để hoạt động dưới tiền tố `/dashboard_crypto/`; không cần tên miền riêng. Artifact chỉ gồm dashboard, trang mở đầu và metadata bản xuất. Report, OOS, health và source catalog không được đưa vào site Pages. Các liên kết đến những trang đó được bỏ khỏi bản xuất; dữ liệu phân tích, scripts và styles của dashboard giữ nguyên.

**Dữ liệu và worker**

Trang hiển thị bản runtime mới nhất của worker đã lưu checkpoint và deploy thành công. Không cần commit raw data/model/ledger vào `main`; dữ liệu bền vững nằm trong Releases mã hóa và nhánh `worker-state`. Sau khi bàn giao thành công, Windows được tạm dừng và máy cá nhân có thể tắt. Xem [hướng dẫn worker](GITHUB_ACTIONS_WORKER.vi.md).

GitHub Pages phục vụ HTML/JS tĩnh. Worker chạy trên Actions; receipts, models, nhãn và evaluation gate giữ trong payload mã hóa. Các liên kết phụ lục cần bộ artifact đầy đủ được mô tả ở [phạm vi repository](GITHUB_REPOSITORY.vi.md).

**Kiểm tra trước khi push snapshot**

```powershell
py -3.11 tools/export_public_dashboard.py --dashboard-only
py -3.11 tools/check_public_dashboard.py --dashboard-only
```

Các kiểm tra này dùng standard library; không train hoặc thay đổi mô hình. Xem `build_info.json` để đối chiếu commit và hashes của files đã xuất.

Tài liệu tham khảo: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
