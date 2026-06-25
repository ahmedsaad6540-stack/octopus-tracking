-- OCTOPUS V3.1 – Tracking Core (Production)
-- PostgreSQL / Supabase
-- Run in Supabase SQL Editor

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- PRODUCTS
create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  niche text not null,
  network text not null,
  commission_usd numeric(10,2) not null,
  epc numeric(10,4) default 0,
  affiliate_url text not null,
  is_active boolean default true,
  created_at timestamptz default now()
);
create index if not exists idx_products_niche on products(niche);

-- VIDEOS
create table if not exists videos (
  id uuid primary key default gen_random_uuid(),
  hook text not null,
  niche text not null,
  product_id uuid references products(id),
  tiktok_url text,
  published_at timestamptz default now(),
  views_platform int default 0,
  views_tracked int default 0,
  views int generated always as (greatest(views_platform, views_tracked)) stored
);

-- CLICKS
create table if not exists clicks (
  id uuid primary key default gen_random_uuid(),
  video_id uuid references videos(id) on delete set null,
  product_id uuid references products(id),
  ip_hash text not null,
  ua_hash text not null,
  platform text default 'tiktok',
  referrer text,
  country text,
  bot_flag boolean default false,
  duplicate_flag boolean default false,
  risk_score int default 0,
  created_at timestamptz default now()
);
create index if not exists idx_clicks_video on clicks(video_id);
create index if not exists idx_clicks_created on clicks(created_at desc);

-- CONVERSIONS
create table if not exists conversions (
  id uuid primary key default gen_random_uuid(),
  click_id uuid references clicks(id) on delete set null,
  video_id uuid references videos(id) on delete set null,
  network text not null,
  sale_amount numeric(10,2),
  sale_currency text default 'USD',
  commission_amount numeric(10,2),
  commission_currency text default 'USD',
  fx_rate numeric(10,6) default 1.0,
  commission_usd numeric(10,2) not null,
  status text default 'approved',
  external_order_id text,
  raw_payload jsonb,
  received_at timestamptz default now(),
  unique(external_order_id, network)
);

-- IMMUTABILITY
create or replace function forbid_update() returns trigger language plpgsql as $$
begin raise exception 'table % is append-only', TG_TABLE_NAME; end $$;
drop trigger if exists clicks_no_update on clicks;
create trigger clicks_no_update before update on clicks for each row execute function forbid_update();
drop trigger if exists conversions_no_update on conversions;
create trigger conversions_no_update before update on conversions for each row execute function forbid_update();

-- ROI VIEW
create or replace view v_video_roi as
select
  v.id as video_id, v.hook, v.niche,
  p.name as product_name, p.network,
  coalesce(v.views_platform, v.views, 0) as views,
  count(distinct c.id) filter (where c.bot_flag = false) as clicks_real,
  count(distinct conv.id) filter (where conv.status = 'approved') as sales,
  coalesce(sum(conv.commission_usd) filter (where conv.status = 'approved'),0) as revenue_usd,
  case when count(distinct c.id) filter (where c.bot_flag = false) > 0 then
    round(count(distinct conv.id) filter (where conv.status='approved')::numeric
      / count(distinct c.id) filter (where c.bot_flag = false) * 100, 2)
    else 0 end as conversion_rate,
  case when coalesce(v.views_platform, v.views,0) > 0 then
    round(count(distinct c.id) filter (where c.bot_flag = false)::numeric
      / coalesce(v.views_platform, v.views,0) * 100, 2)
    else 0 end as ctr,
  case when count(distinct c.id) filter (where c.bot_flag = false) > 0 then
    round(sum(conv.commission_usd) filter (where conv.status='approved')::numeric
      / count(distinct c.id) filter (where c.bot_flag = false), 4)
    else 0 end as epc,
  case when coalesce(v.views_platform, v.views,0) > 0 then
    round(sum(conv.commission_usd) filter (where conv.status='approved')::numeric
      / coalesce(v.views_platform, v.views,0) * 1000, 4)
    else 0 end as rpvm
from videos v
left join products p on p.id = v.product_id
left join clicks c on c.video_id = v.id
left join conversions conv on conv.click_id = c.id
group by v.id, p.name, p.network, p.commission_usd
order by revenue_usd desc, clicks_real desc;

-- Seed 20 products
insert into products (name, niche, network, commission_usd, epc, affiliate_url) values
('Budget Planner Sheet PRO', 'مال', 'impact', 26.00, 1.60, 'https://example.com/budget'),
('Notion Finance OS', 'مال', 'digistore24', 12.00, 1.80, 'https://example.com/notion-finance'),
('Investing Course KSA', 'مال', 'digistore24', 47.00, 2.10, 'https://example.com/investing'),
('Expense Tracker App', 'مال', 'impact', 8.50, 1.20, 'https://example.com/expense'),
('Credit Score Guide', 'مال', 'partnerstack', 19.00, 1.45, 'https://example.com/credit'),
('AI Resume Builder Pro', 'تك', 'digistore24', 38.00, 2.40, 'https://example.com/ai-resume'),
('VPN Yearly Premium', 'تك', 'impact', 45.00, 2.10, 'https://example.com/vpn'),
('AI Video Generator', 'تك', 'partnerstack', 32.00, 2.80, 'https://example.com/ai-video'),
('Notion AI Templates', 'تك', 'digistore24', 15.00, 1.90, 'https://example.com/notion-ai'),
('Cloud Hosting 1Y', 'تك', 'impact', 55.00, 1.70, 'https://example.com/hosting'),
('Niacinamide Serum', 'beauty', 'amazon_eg', 1.20, 0.35, 'https://amazon.eg/dp/test'),
('Vitamin C Serum', 'beauty', 'noon', 2.10, 0.42, 'https://noon.com/test'),
('Skin Routine Course', 'beauty', 'digistore24', 22.00, 1.55, 'https://example.com/skin-course'),
('Derma Roller Pro', 'beauty', 'amazon_sa', 3.80, 0.51, 'https://amazon.sa/dp/test'),
('Korean Skincare Box', 'beauty', 'impact', 14.00, 0.88, 'https://example.com/k-beauty'),
('Relationship Communication Course', 'علاقات', 'digistore24', 29.00, 1.95, 'https://example.com/rel-course'),
('Couples Therapy App 1Y', 'علاقات', 'partnerstack', 18.00, 1.30, 'https://example.com/couples-app'),
('Attachment Style Guide', 'علاقات', 'digistore24', 14.00, 1.60, 'https://example.com/attachment'),
('Marriage Save Blueprint', 'علاقات', 'digistore24', 41.00, 2.20, 'https://example.com/marriage'),
('Dating Profile Optimizer AI', 'علاقات', 'impact', 9.00, 1.15, 'https://example.com/dating-ai')
on conflict do nothing;
