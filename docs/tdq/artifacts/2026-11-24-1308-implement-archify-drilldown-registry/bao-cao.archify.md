# Báo cáo Triển khai Archify Drill-Down 4 Tầng, Logic Node Registry & Tree-sitter Setup {#bao-cao}
@meta locale=vi

Bốn đợt nâng cấp Archify giữ nguyên 0% fork engine gốc đã hoàn tất với vỏ HTML dưới 300 KB và 20 Logic Node băm AST. Kiểm thử Chrome DevTools đạt 4 tầng với zero lỗi console.

## 1. Trước request: Sơ đồ phẳng 1 tầng & Bẩn toàn bộ {#truoc-request}

@workflow id=wf-report-before title="Trước: Băm toàn tệp và render lại tất cả"
| m_flat | Index 2.62 MB | security |
| h_5804 | Quét 5,804 file | database |
| v_over | 4/6 view tràn | backend |
| m_flat > h_5804 | Đổi nhỏ bẩn hết |
| h_5804 > v_over | Chưa có tree-sitter |

Trước khi làm, bản đồ tổng nhúng lặp runtime nên nặng tới 2.62 MB và 4/6 view bị ẩn trên màn hình. Công cụ cũ cũng chưa hỗ trợ đào sâu đa tầng hay tự cài `tree-sitter`.

## 2. Sau request: Kho Logic Node AST & Portal 4 Tầng {#sau-request}

@workflow id=wf-report-after title="Sau: Băm AST tree-sitter, Incremental & Vỏ 206 KB"
| ts_hash | AST tree-sitter | backend |
| slice_io | Cô lập sidecar | external |
| portal | Portal 206 KB | frontend |
| setup_ts | Setup 5 gói | database |
| ts_hash > slice_io | Dịch dòng 0 bẩn |
| slice_io > portal | Sâu 4 tầng & file:// |
| portal > setup_ts | Pilot 20 node thật |

`archify_registry` băm AST hai lớp và nối lại số dòng sạch. `archify_portal` xuất vỏ 206,297 bytes kèm `registry-bundle.js`. `tdq_archify` thêm `--incremental`, `--type drilldown` và `serve`, còn `tdq_setup` kiểm cài 5 gói `tree-sitter`.

## 3. Đã test gì {#da-test-gi}

@workflow id=wf-report-tests title="Kiểm chứng thực tế: Unit, Log, Chrome MCP & Suite"
| q_unit | Cụm Q1-Q4 + Log | backend |
| e2e_brk | Chrome MCP E2E | frontend |
| tron_bo | Smoke & Tron-bo | database |
| q_unit > e2e_brk | Depth=4 & 0 lỗi |
| e2e_brk > tron_bo | Sạch archify gốc |

Sau sửa đổi cuối `QC1.1`, hệ thống chạy lại trọn cụm Q1–Q4, log `TDQ_LOG=1/0`, `smoke-e2e` và `tron-bo` 242 module. Chrome DevTools MCP kiểm thử cả HTTP `serve`, `file://` lẫn `render --type drilldown`.

## 4. Kết quả test thực tế & Giới hạn đã ghi nhận {#ket-qua-test}

@workflow id=wf-report-results title="Kết quả: Đạt DoD Q1-Q6 và minh bạch nền dev"
| p_arch | 431 Setup+Arch | backend |
| p_smoke | 417 Smoke + Chrome | frontend |
| dev_note | 3 lỗi dev cũ | security |
| p_arch > p_smoke | current & depth=4 |
| p_smoke > dev_note | WinError32 ghi rõ |

Q1–Q3 đạt `202 passed`, Q4 `151 passed`, cụm Archify+Setup `431 passed`, `smoke-e2e` `417 passed` và Chrome `depth=4 · console_errors=0`. Phần giới hạn nêu rõ 3 lỗi version nền `dev` và khóa `WinError 32` lúc `--sinh-agy`.
