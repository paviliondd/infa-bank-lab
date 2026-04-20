#!/bin/bash
# Lab 5.1 Capstone - Stress/Load Testing Script
# Simulate thousands of users and transaction requests to trigger AIOps alerts.

TARGET_URL="https://bank.linuxunity.com"

echo "========================================================="
echo "   🏦 KÍCH HOẠT QUÁ TRÌNH TẤN CÔNG TẢI BẰNG HÀNG LOẠT   "
echo "========================================================="
echo "Đang giả lập traffic tới: $TARGET_URL"
echo ""

# Tính năng 1: Gửi request bình thường tới trang chủ (Tạo traffic HTTP HTTP 200)
fun_home_traffic() {
    while true; do
        curl -s -o /dev/null -w "GET Home: %{http_code}\n" $TARGET_URL/
        sleep 0.1
    done
}

# Tính năng 2: Giao dịch chuyển tiền (Sẽ tăng CPU đột biến & tăng count metric)
fun_transfer_spam() {
    while true; do
        # Ngẫu nhiên số tiền từ 10$ đến 5000$
        AMOUNT=$((RANDOM % 5000 + 10))
        curl -s -X POST "$TARGET_URL/transfer?amount=$AMOUNT" -o /dev/null -w "POST Transfer: \$${AMOUNT}\n"
        sleep 0.05
    done
}

# Mở nhiều luồng chạy song song
for i in {1..5}; do
    fun_home_traffic &
    fun_transfer_spam &
done

echo "🔥 Đã thả 10 luồng tấn công. Nhấn Ctrl+C để dừng."
echo "Truy cập Grafana Dashboard ngay để xem Prometheus Rules kích hoạt!"
wait
