use teloxide::{prelude::*, types::{InlineKeyboardMarkup, InlineKeyboardButton}};
use sqlx::{SqlitePool, FromRow};
use serde::{Deserialize, Serialize};
use reqwest::blocking::Client;
use image::{open, ImageOutputFormat};
use std::{env, time::{SystemTime, UNIX_EPOCH}, collections::HashMap};
use tokio::time;

#[tokio::main]
async fn main() {
    let pool = SqlitePool::connect("sqlite:bot.db").await.unwrap();
    sqlx::query("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, chat_id INTEGER, state TEXT, lang TEXT, y INTEGER, m INTEGER, d INTEGER)").execute(&pool).await.unwrap();
    sqlx::query("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, y INTEGER, m INTEGER, d INTEGER, t TEXT)").execute(&pool).await.unwrap();
    sqlx::query("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, r DATE)").execute(&pool).await.unwrap();

    let bot = Bot::from_env();
    let pool_c = pool.clone();
    tokio::spawn(async move {
        let mut interval = time::interval(time::Duration::from_secs(60));
        loop {
            interval.tick().await;
            let rs = sqlx::query_as::<_, (i64, i64)>("SELECT u.user_id, u.chat_id FROM reminders r JOIN users u ON r.user_id = u.user_id WHERE r.r = date('now')").fetch_all(&pool_c).await.unwrap();
            for (_, c) in rs {
                bot.send_message(ChatId(c), "Happy Birthday!").await.unwrap();
            }
        }
    });

    let langs = HashMap::from([
        ("en", HashMap::from([("y", "Select birth year:"), ("m", "Select birth month:"), ("d", "Select birth day:"), ("i", "📅 Info:\nPersian: %s\nGregorian: %s\nHijri: %s\nAge: %d\nZodiac: %s\nHoliday: %s"), ("e", "Invalid input"), ("p", "Moon phase"), ("s", "Share/reset:"), ("r", "Reset"), ("h", "History"), ("n", "No history"), ("l", "Select language:")])),
        ("fa", HashMap::from([("y", "سال تولد:"), ("m", "ماه تولد:"), ("d", "روز تولد:"), ("i", "📅 اطلاعات:\nشمسی: %s\nمیلادی: %s\nقمری: %s\nسن: %d\nزودیاک: %s\nتعطیلات: %s"), ("e", "ورودی نامعتبر"), ("p", "فاز ماه"), ("s", "اشتراک/شروع مجدد:"), ("r", "شروع مجدد"), ("h", "تاریخچه"), ("n", "تاریخچه‌ای یافت نشد"), ("l", "انتخاب زبان:")])),
    ]);

    let handler = Update::filter_message()
        .branch(dptree::entry()
            .filter_command::<Command>()
            .endpoint(move |bot, update, cmd| {
                let pool = pool.clone();
                let langs = langs.clone();
                async move {
                    match cmd {
                        Command::Start => {
                            let c = update.chat().id;
                            let i = update.from().unwrap().id;
                            let l = update.from().unwrap().language_code.as_ref().map(|l| l.as_str()).unwrap_or("en");
                            let l = if langs.contains_key(l) { l } else { "en" };
                            sqlx::query("INSERT OR REPLACE INTO users (user_id, chat_id, state, lang, y, m, d) VALUES (?, ?, ?, ?, NULL, NULL, NULL)")
                                .bind(i).bind(c).bind("y").bind(l).execute(&pool).await.unwrap();
                            bot.send_message(c, langs[l]["y"]).reply_markup(kb((1385..=1339).rev().collect(), "y", 4)).await.unwrap();
                        }
                        Command::Lang => {
                            let c = update.chat().id;
                            let l = update.from().unwrap().language_code.as_ref().map(|l| l.as_str()).unwrap_or("en");
                            bot.send_message(c, langs[l]["l"]).reply_markup(kb(vec!["en|English", "fa|فارسی", "es|Español", "zh|中文", "hi|हिन्दी", "ar|العربية", "pt|Português", "ru|Русский", "fr|Français", "de|Deutsch", "ja|日本語"], "l", 3)).await.unwrap();
                        }
                    }
                    Ok(())
                }
            }))
        .branch(Update::filter_callback_query()
            .endpoint(move |bot, update, q| {
                let pool = pool.clone();
                let langs = langs.clone();
                async move {
                    let c = q.message.unwrap().chat.id;
                    let i = q.from.id;
                    let (p, v) = q.data.unwrap().split_once("|").unwrap();
                    let mut u: User = sqlx::query_as("SELECT * FROM users WHERE user_id = ?").bind(i).fetch_one(&pool).await.unwrap_or(User { user_id: i, chat_id: c.0, state: "y".into(), lang: "en".into(), y: None, m: None, d: None });
                    let l = u.lang.as_str();

                    match p {
                        "l" => {
                            u.lang = v.into();
                            sqlx::query("UPDATE users SET lang = ? WHERE user_id = ?").bind(&u.lang).bind(i).execute(&pool).await.unwrap();
                            bot.send_message(c, langs[l]["y"]).reply_markup(kb((1385..=1339).rev().collect(), "y", 4)).await.unwrap();
                        }
                        "r" => {
                            u.state = "y".into();
                            u.y = None; u.m = None; u.d = None;
                            sqlx::query("UPDATE users SET state = ?, y = NULL, m = NULL, d = NULL WHERE user_id = ?").bind(&u.state).bind(i).execute(&pool).await.unwrap();
                            bot.send_message(c, langs[l]["y"]).reply_markup(kb((1385..=1339).rev().collect(), "y", 4)).await.unwrap();
                        }
                        "h" => {
                            let h = sqlx::query_as::<_, History>("SELECT y, m, d, t FROM history WHERE user_id = ?").bind(i).fetch_all(&pool).await.unwrap();
                            let t = format!("{}\n{}", langs[l]["h"], if h.is_empty() { langs[l]["n"].to_string() } else { h.iter().map(|x| format!("{}/{}/{} ({})", p(x.y), p(x.m), p(x.d), x.t)).collect::<Vec<_>>().join("\n") });
                            bot.send_message(c, t).await.unwrap();
                        }
                        _ => {
                            let v: i32 = v.parse().unwrap();
                            match p {
                                "y" if !(1340..=1385).contains(&v) => bot.send_message(c, langs[l]["e"]).await.unwrap(),
                                "m" if !(1..=12).contains(&v) => bot.send_message(c, langs[l]["e"]).await.unwrap(),
                                "d" if !(1..=31).contains(&v) || !vj(u.y.unwrap_or(1340), u.m.unwrap_or(1), v) => bot.send_message(c, langs[l]["e"]).await.unwrap(),
                                _ => {
                                    match p {
                                        "y" => {
                                            u.y = Some(v);
                                            u.state = "m".into();
                                            sqlx::query("UPDATE users SET y = ?, state = ? WHERE user_id = ?").bind(v).bind(&u.state).bind(i).execute(&pool).await.unwrap();
                                            bot.send_message(c, langs[l]["m"]).reply_markup(kb((1..=12).collect(), "m", 4)).await.unwrap();
                                        }
                                        "m" => {
                                            u.m = Some(v);
                                            u.state = "d".into();
                                            sqlx::query("UPDATE users SET m = ?, state = ? WHERE user_id = ?").bind(v).bind(&u.state).bind(i).execute(&pool).await.unwrap();
                                            bot.send_message(c, langs[l]["d"]).reply_markup(kb((1..=31).collect(), "d", 5)).await.unwrap();
                                        }
                                        "d" => {
                                            u.d = Some(v);
                                            u.state = "x".into();
                                            let g = jg(u.y.unwrap(), u.m.unwrap(), v);
                                            sqlx::query("UPDATE users SET d = ?, state = ? WHERE user_id = ?").bind(v).bind(&u.state).bind(i).execute(&pool).await.unwrap();
                                            sqlx::query("INSERT INTO history (user_id, y, m, d, t) VALUES (?, ?, ?, ?, ?)")
                                                .bind(i).bind(u.y.unwrap()).bind(u.m.unwrap()).bind(v).bind(g.format("%Y-%m-%d")).execute(&pool).await.unwrap();
                                            sqlx::query("INSERT INTO reminders (user_id, r) VALUES (?, ?)")
                                                .bind(i).bind(g.checked_add_months(12).unwrap().format("%Y-%m-%d")).execute(&pool).await.unwrap();
                                            bot.send_message(c, format!(langs[l]["i"], format!("{}/{}/{}", p(u.y.unwrap()), p(u.m.unwrap()), p(u.d.unwrap())), g.format("%Y-%m-%d"), hijri(&g).await, (SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64 - g.unix_timestamp()) / 3600 / 24 / 365, z(&g), holiday(&g).await)).await.unwrap();
                                            let p = moon(&g).await;
                                            bot.send_photo(c, teloxide::types::InputFile::file(&p), Some(langs[l]["p"])).await.unwrap();
                                            bot.send_message(c, langs[l]["s"]).reply_markup(kb(vec![
                                                format!("Twitter|https://twitter.com/intent/tweet?text={}", g.format("%Y-%m-%d")),
                                                format!("Instagram|https://instagram.com/stories?date={}", g.format("%Y-%m-%d")),
                                                format!("{}|r", langs[l]["r"]),
                                                format!("{}|h", langs[l]["h"])
                                            ], "s", 2)).await.unwrap();
                                            std::fs::remove_file(p).unwrap();
                                        }
                                        _ => {}
                                    }
                                }
                            }
                        }
                    }
                    Ok(())
                }
            }));

    teloxide::repl_with_listener(bot, handler, teloxide::adaptors::DefaultBotCommands::new()).await;
}

#[derive(Debug, FromRow)]
struct User {
    user_id: i64,
    chat_id: i64,
    state: String,
    lang: String,
    y: Option<i32>,
    m: Option<i32>,
    d: Option<i32>,
}

#[derive(Debug, FromRow)]
struct History {
    y: i32,
    m: i32,
    d: i32,
    t: String,
}

#[derive(Debug, Clone)]
enum Command {
    Start,
    Lang,
}

impl teloxide::utils::command::BotCommands for Command {
    fn parse(s: &str, _bot_name: &str) -> Option<Self> {
        match s {
            "/start" => Some(Command::Start),
            "/language" => Some(Command::Lang),
            _ => None,
        }
    }
}

fn p(n: i32) -> String {
    let persian = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
    n.to_string().chars().map(|c| persian[c.to_digit(10).unwrap() as usize]).collect()
}

fn kb(items: Vec<i32>, p: &str, r: i32) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(
        items.chunks(r as usize).map(|c| 
            c.iter().map(|&i| InlineKeyboardButton::callback(p(i), format!("{}|{}", p, i))).collect::<Vec<_>>()
        ).collect::<Vec<_>>()
    ).unwrap()
}

fn vj(y: i32, m: i32, d: i32) -> bool {
    !(m > 12 || d > 31 || y < 1340 || y > 1385 || (m > 6 && d > 30) || (m == 12 && d == 30 && (y % 4 == 2 || y % 4 == 3)))
}

fn jg(y: i32, m: i32, d: i32) -> chrono::NaiveDate {
    let jd = y * 365 + y / 4 + m * 30 + d - 428 - if m > 6 { 6 } else { 0 };
    let gd = jd + 226899;
    chrono::NaiveDate::from_ymd_opt(gd / 365, ((gd % 365) / 30 + 1) as u32, ((gd % 365) % 30 + 1) as u32).unwrap()
}

async fn hijri(d: &chrono::NaiveDate) -> String {
    let key = format!("hijri_{}", d.format("%Y-%m-%d"));
    if let Some(c) = CACHE.read().await.get(&key) {
        if SystemTime::now().duration_since(c.t).unwrap().as_secs() < 86400 {
            return c.v.clone();
        }
    }
    let r = Client::new().get(format!("https://api.aladhan.com/v1/gToH?date={}", d.format("%d-%m-%Y"))).send().unwrap().json::<serde_json::Value>().unwrap();
    let v = format!("{} {} {}", r["data"]["hijri"]["day"], r["data"]["hijri"]["month"]["en"], r["data"]["hijri"]["year"]);
    CACHE.write().await.insert(key, CacheEntry { v: v.clone(), t: SystemTime::now() });
    v
}

fn z(d: &chrono::NaiveDate) -> String {
    let (m, d) = (d.month() as i32, d.day() as i32);
    match () {
        _ if (m == 3 && d >= 21) || (m == 4 && d <= 19) => "Aries",
        _ if (m == 4 && d >= 20) || (m == 5 && d <= 20) => "Taurus",
        _ if (m == 5 && d >= 21) || (m == 6 && d <= 20) => "Gemini",
        _ if (m == 6 && d >= 21) || (m == 7 && d <= 22) => "Cancer",
        _ if (m == 7 && d >= 23) || (m == 8 && d <= 22) => "Leo",
        _ if (m == 8 && d >= 23) || (m == 9 && d <= 22) => "Virgo",
        _ if (m == 9 && d >= 23) || (m == 10 && d <= 22) => "Libra",
        _ if (m == 10 && d >= 23) || (m == 11 && d <= 21) => "Scorpio",
        _ if (m == 11 && d >= 22) || (m == 12 && d <= 21) => "Sagittarius",
        _ if (m == 12 && d >= 22) || (m == 1 && d <= 19) => "Capricorn",
        _ if (m == 1 && d >= 20) || (m == 2 && d <= 18) => "Aquarius",
        _ => "Pisces",
    }.to_string()
}

async fn holiday(d: &chrono::NaiveDate) -> String {
    let key = format!("holiday_{}", d.format("%Y-%m-%d"));
    if let Some(c) = CACHE.read().await.get(&key) {
        if SystemTime::now().duration_since(c.t).unwrap().as_secs() < 86400 {
            return c.v.clone();
        }
    }
    let r = Client::new().get(format!("https://calendarific.com/api/v2/holidays?api_key={}&country=IR&year={}&month={}&day={}", env::var("CALENDARIFIC_API_KEY").unwrap(), d.year(), d.month(), d.day())).send().unwrap().json::<serde_json::Value>().unwrap();
    let v = r["response"]["holidays"].as_array().and_then(|h| h.get(0).and_then(|x| x["name"].as_str())).unwrap_or("No holiday").to_string();
    CACHE.write().await.insert(key, CacheEntry { v: v.clone(), t: SystemTime::now() });
    v
}

async fn moon(d: &chrono::NaiveDate) -> String {
    let key = format!("moon_{}", d.format("%Y-%m-%d"));
    if let Some(c) = CACHE.read().await.get(&key) {
        if SystemTime::now().duration_since(c.t).unwrap().as_secs() < 86400 {
            return c.v.clone();
        }
    }
    let r = Client::new().get(format!("https://api.nasa.gov/planetary/apod?api_key={}&date={}", env::var("NASA_API_KEY").unwrap(), d.format("%Y-%m-%d"))).send().unwrap().json::<serde_json::Value>().unwrap();
    let mut img = open(&reqwest::blocking::get(r["url"].as_str().unwrap()).unwrap().bytes().unwrap()[..]).unwrap();
    let wm = open("watermark.png").unwrap();
    image::imageops::overlay(&mut img, &wm, (img.width() - wm.width() - 10).into(), (img.height() - wm.height() - 10).into());
    let path = format!("/tmp/moon_{}.jpg", d.format("%Y%m%d"));
    let mut f = std::fs::File::create(&path).unwrap();
    img.write(&mut f, ImageOutputFormat::Jpeg(85)).unwrap();
    CACHE.write().await.insert(key, CacheEntry { v: path.clone(), t: SystemTime::now() });
    path
}

#[macro_use] extern crate lazy_static;
lazy_static::lazy_static! {
    static ref CACHE: tokio::sync::RwLock<HashMap<String, CacheEntry>> = tokio::sync::RwLock::new(HashMap::new());
}

#[derive(Clone)]
struct CacheEntry {
    v: String,
    t: SystemTime,
}