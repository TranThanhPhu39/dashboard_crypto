# FOMC identification và timing — 19/10/2026

Đã thực hiện audit trước fit, snapshot author repository theo commit, cùng75 scheduled events cho BTC/ETH và32 outcomes, trong đó23 pre2020 và52 post2020.

[Báo cáo](../outputs/research/fomc_identification_20261019/report.html) · [Markdown](../outputs/research/fomc_identification_20261019/report.md) · [dashboard](../outputs/research/fomc_identification_20261019/dashboard.html) · [thiết kế khóa](../config/fomc_identification_20261019.json).

Nguồn chính là maintained Jarocinski–Karadi median components, không thay STMT bằng một nhãn policy tự tạo. PCA và median rotation tái lập trong rounding tolerance. Dùng Coinbase USD cho cả minute và daily để so intraday/event-day/post1…30 trên cùng nguồn và events. FullBH128, periodsBH256, direct timing differencesBH8 tách family. CI conditional, không bao gồm đầy đủ generated-shock uncertainty.

Tại median, intraday policy coefficients khoảng−1,163%BTC và−1,422%ETH per+10bps contribution to pc1, cùng đạtBH128. Dấu âm giữ ở3 rotations và75 single-event deletions đã kiểm tra. Có3/128 full coefficients đạtBH;0/8 direct timing differences đạtBH. Không suy từ đây ra causal certainty, persistence hay future predictive skill. Độ nhạy3 rotations không phải toàn bộ identified set; deletion là post-hoc diagnostic đã khai báo riêng.

Không sửa baseline, latency40models, prospective protocol, monetary stress hoặc jointVAR. Stage `sources/audit/fit/influence/validate/product` lưu riêng và có old-file hash guards. ZIP mới là supplement cho repo hiện tại, không standalone và không lặp lại các archive/model bundle cũ.
