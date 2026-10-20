**Dashboard miễn phí trên GitHub Pages**

Địa chỉ dự kiến sau khi workflow deploy thành công:

- Dashboard: https://tranthanhphu39.github.io/dashboard_crypto/dashboard/
- Metadata bản xuất: https://tranthanhphu39.github.io/dashboard_crypto/build_info.json

**Cách cập nhật**

Workflow `.github/workflows/pages.yml` kiểm tra bản xuất khi có pull request vào `main`. Sau khi push/merge vào `main`, workflow xuất riêng dashboard, xác minh hashes và đường dẫn chính, upload artifact `public-pages/`, rồi triển khai GitHub Pages qua môi trường `github-pages`. PR chỉ build/kiểm tra, không deploy.

Theo dõi tại https://github.com/TranThanhPhu39/dashboard_crypto/actions . Có thể chạy lại bằng `Actions -> Publish dashboard to GitHub Pages -> Run workflow`, chọn `main`.

Trong `Settings -> Pages`, nguồn xuất bản dùng `GitHub Actions`. Dashboard sử dụng các đường dẫn tương đối để hoạt động dưới tiền tố `/dashboard_crypto/`; không cần tên miền riêng. Artifact chỉ gồm dashboard, trang mở đầu và metadata bản xuất. Report, OOS, health và source catalog không được đưa vào site Pages. Các liên kết đến những trang đó được bỏ khỏi bản xuất; dữ liệu phân tích, scripts và styles của dashboard giữ nguyên.

**Dữ liệu và worker**

Trang hiển thị snapshot có trong commit đã deploy. Worker Windows tiếp tục thu dữ liệu/dự báo theo lịch hiện tại. Khi worker cập nhật file ở máy nghiên cứu, các file đó chưa tự trở thành commit GitHub. Cần quy trình đồng bộ snapshot riêng để tự đưa dữ liệu mới lên web; workflow này tự xuất bản những gì đã được đưa vào `main`.

GitHub Pages phục vụ HTML/JS tĩnh. Worker OOS, receipts, models, nhãn và evaluation gate vẫn nằm trong quy trình nghiên cứu riêng. Các liên kết phụ lục cần bộ artifact đầy đủ được mô tả ở [phạm vi repository](GITHUB_REPOSITORY.vi.md).

**Kiểm tra trước khi push snapshot**

```powershell
py -3.11 tools/export_public_dashboard.py --dashboard-only
py -3.11 tools/check_public_dashboard.py --dashboard-only
```

Các kiểm tra này dùng standard library; không train hoặc thay đổi mô hình. Xem `build_info.json` để đối chiếu commit và hashes của files đã xuất.

Tài liệu tham khảo: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
