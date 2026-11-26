'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, 'dist/owner.js'), 'utf8') + '\nglobalThis.core = BerrabaiCore;', context);
const core = context.core;
const raw = core.parseCSV(fs.readFileSync(path.join(root, 'examples/sample-orders.csv'), 'utf8'));
const keys = ['orderId','lineId','date','product','color','qty','paid','refund','refundQty','status'];
const mapping = Object.fromEntries(keys.map((key, i) => [key, String(i)]));
const orders = core.normalize(raw, mapping);

test('synthetic fixture matches independently calculated weekly totals', () => {
  assert.equal(orders.length, 70);
  const result = core.summarize(orders, '2026-11-19', '2026-11-25');
  assert.equal(result.orders, 24);
  assert.equal(result.quantity, 58);
  assert.equal(result.paid, 3123400);
  assert.equal(result.refund, 134000);
  assert.equal(result.revenue, 2989400);
  assert.equal(result.previous.revenue, 2057000);
  assert.equal(result.previous.orders, 24);
  assert.equal(result.previous.quantity, 55);
  assert.equal(result.daily.reduce((sum, day) => sum + day.revenue, 0), result.revenue);
});

test('missing colors stay separate and refunds reduce units only when specified', () => {
  const result = core.summarize(orders, '2026-11-19', '2026-11-25');
  const colors = Object.fromEntries(result.colors.map(c => [c.name, c]));
  assert.equal(colors['粉色'].quantity, 24);
  assert.equal(colors['紫色'].quantity, 21);
  assert.equal(colors['黄色'].quantity, 10);
  assert.equal(colors['未填写'].quantity, 3);
  const base = {orderId:'A',date:'2026-11-25',product:'Test',color:'',qty:2,refundQty:0,paid:10000,refund:5000,status:'已支付'};
  const single = core.summarize([base, {...base,orderId:'B',status:'已取消'}], '2026-11-25','2026-11-25');
  assert.equal(single.orders, 1);
  assert.equal(single.quantity, 2);
  assert.equal(single.revenue, 5000);
});

test('CSV accepts quoted commas, escaped quotes, multiline fields and UTF-8 BOM', () => {
  const result = core.parseCSV('\uFEFFa,b\r\n"hello, world","a""b\nc"\r\n');
  assert.equal(result.rows[0][0], 'hello, world');
  assert.equal(result.rows[0][1], 'a"b\nc');
  assert.throws(() => core.parseCSV('a,b\n"unfinished,b'), /引号/);
  assert.throws(() => core.parseCSV('a,a\n1,2'), /重复列名/);
});

test('invalid amounts, quantities, dates and reversed ranges are rejected', () => {
  for (const amount of ['-1', 'Infinity', '1.234', 'NaN']) assert.throws(() => core.cents(amount));
  assert.equal(core.cents('￥1,234.56'), 123456);
  for (const [column, value] of [[2,'2026-02-30'], [5,'-1'], [6,'-1'], [7,'999999'], [8,'999']]) {
    const row = Array.from(raw.rows[0]); row[column] = value;
    assert.throws(() => core.normalize({rows:[row]}, mapping));
  }
  assert.throws(() => core.summarize(orders,'2026-11-25','2026-11-19'));
  assert.throws(() => core.summarize(orders,'2026-02-30','2026-03-02'));
  assert.throws(() => core.summarize(orders,'2025-01-01','2026-11-25'));
});

test('line identity survives refund updates and separates multi-line orders', () => {
  const updated = Array.from(raw.rows[0]); updated[7] = '100';
  const [row] = core.normalize({rows:[updated]}, mapping);
  assert.equal(row.id, orders[0].id);
  const two = Array.from(updated); two[1] = 'different-line';
  assert.notEqual(core.normalize({rows:[two]}, mapping)[0].id, row.id);
});

test('unknown or missing status never becomes paid revenue', () => {
  const row = orders[0];
  const result = core.summarize(['', undefined, '神秘状态', '待核对', '待支付'].map((status,i)=>({...row,orderId:String(i),status})),row.date,row.date);
  assert.equal(result.orders, 0);
  assert.equal(result.revenue, 0);
  assert.equal(result.unrecognizedStatus, 5);
  const blank = Array.from(raw.rows[0]); blank[9]='';
  assert.equal(core.normalize({rows:[blank]},mapping)[0].status,'待核对');
  assert.equal(core.normalize({rows:[blank]},{...mapping,status:''})[0].status,'待核对');
  for(const status of ['已支付','已发货','已完成','部分退款','已退款']) assert.equal(core.isPaidStatus(status), true);
});

test('daily and weekly report ranges and comparison labels ignore page period', () => {
  const day = core.reportRange('day','2026-11-26','2026-10-28','2026-11-26');
  assert.equal(day.join(','),'2026-11-25,2026-11-25');
  const week = core.reportRange('week','2026-11-26','2026-10-28','2026-11-26');
  assert.equal(week.join(','),'2026-11-19,2026-11-25');
  const d = core.summarize(orders,...day), w = core.summarize(orders,...week);
  assert.match(core.comparison(d.revenue,d.previous.revenue,d.previous.lines,d.days),/比前1天/);
  assert.match(core.comparison(w.revenue,w.previous.revenue,w.previous.lines,w.days),/比前7天/);
});
