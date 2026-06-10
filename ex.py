Kp, Ki, Kd = 0.05, 0.01, 0.03
Ts = 0.03
ref = 0.2
y, u, prev_error, sum_error = 0.0, 0.0, 0.0, 0.0
t_arr, y_arr, u_arr = [], [], []

start_control()
for k in range(300):
    y = read_output()
    error = ref - y
    u = Kp*error + Ki*sum_error + Kd*(error - prev_error)/Ts
    u = max(min(u, 1.0), 0.0)
    apply_input(u)
    prev_error = error
    sum_error += error
    t_arr.append(k * Ts)
    y_arr.append(y)
    u_arr.append(u)
stop_control()
