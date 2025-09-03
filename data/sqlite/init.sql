INSERT INTO users (email, balance, currency) VALUES ('1363992060@qq.com', 50.0, 'CNY');

INSERT INTO analysis_jobs (
  user_id,
  ticker,
  ticker_identifier,
  analysts,
  research_depth,
  trigger_type,
  interval_seconds,
  cron_expr,
  next_run_at,
  active
) VALUES (
  1,                           -- 用户ID
  '北方稀土',                        -- 股票代码
  '600111',                 -- 股票的唯一标识符
  '["Market Analyst", "Financial Analyst"]', -- 分析师角色 (JSON 字符串)
  1,                             -- 研究深度 (1, 2, 或 3)
"interval",                        -- 触发类型：执行一次
  60,                          -- 'interval' 类型专用，此处为 NULL
  NULL,                          -- 'cron' 类型专用，此处为 NULL
  strftime('%Y-%m-%d %H:%M:%S','now'),
  1                              -- 任务状态：激活
);