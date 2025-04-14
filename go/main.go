package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"image/jpeg"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/fogleman/gg"
	"github.com/go-telegram-bot-api/telegram-bot-api/v5"
	"github.com/jmoiron/sqlx"
	_ "github.com/mattn/go-sqlite3"
)

type Bot struct {
	db    *sqlx.DB
	bot   *tgbotapi.BotAPI
	lang  map[string]map[string]string
	cache []struct{ k, v string; t time.Time }
}

func main() {
	db, _ := sqlx.Open("sqlite3", "./bot.db")
	bot, _ := tgbotapi.NewBotAPI(os.Getenv("BOT_TOKEN"))
	b := &Bot{
		db:  db,
		bot: bot,
		lang: map[string]map[string]string{
			"en": {"y": "Select birth year:", "m": "Select birth month:", "d": "Select birth day:", "i": "📅 Info:\nPersian: %s\nGregorian: %s\nHijri: %s\nAge: %d\nZodiac: %s\nHoliday: %s", "e": "Invalid input", "p": "Moon phase", "s": "Share/reset:", "r": "Reset", "h": "History", "n": "No history", "l": "Select language:"},
			"fa": {"y": "سال تولد:", "m": "ماه تولد:", "d": "روز تولد:", "i": "📅 اطلاعات:\nشمسی: %s\nمیلادی: %s\nقمری: %s\nسن: %d\nزودیاک: %s\nتعطیلات: %s", "e": "ورودی نامعتبر", "p": "فاز ماه", "s": "اشتراک/شروع مجدد:", "r": "شروع مجدد", "h": "تاریخچه", "n": "تاریخچه‌ای یافت نشد", "l": "انتخاب زبان:"},
		},
	}

	go func() {
		for range time.Tick(time.Minute) {
			var r []struct{ UserID, ChatID int64 }
			db.Select(&r, "SELECT u.user_id, u.chat_id FROM reminders r JOIN users u ON r.user_id = u.user_id WHERE r.r = ?", time.Now().Format("2006-01-02"))
			for _, x := range r {
				b.send(x.ChatID, "Happy Birthday!", nil)
			}
		}
	}()

	http.HandleFunc("/webhook", b.handle)
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func (b *Bot) handle(w http.ResponseWriter, r *http.Request) {
	var u tgbotapi.Update
	json.NewDecoder(r.Body).Decode(&u)

	c := u.Message.Chat.ID
	i := u.Message.From.ID
	if u.CallbackQuery != nil {
		c = u.CallbackQuery.Message.Chat.ID
		i = u.CallbackQuery.From.ID
	}

	var user struct{ State, Lang string; Y, M, D *int }
	b.db.Get(&user, "SELECT state, lang, y, m, d FROM users WHERE user_id = ?", i)
	l := user.Lang
	if l == "" && u.Message != nil {
		l = u.Message.From.LanguageCode
		if _, ok := b.lang[l]; !ok {
			l = "en"
		}
	}

	if m := u.Message; m != nil && m.Text != "" {
		switch m.Text {
		case "/start":
			b.db.Exec("INSERT INTO users (user_id, chat_id, state, lang) VALUES (?, ?, ?, ?) ON DUPLICATE KEY UPDATE state = ?, y = NULL, m = NULL, d = NULL", i, c, "y", l, "y")
			b.send(c, b.t(l, "y"), b.kb(r(1385, 1340), "y", 4))
		case "/language":
			b.send(c, b.t(l, "l"), b.kb([]string{"en|English", "fa|فارسی", "es|Español", "zh|中文", "hi|हिन्दी", "ar|العربية", "pt|Português", "ru|Русский", "fr|Français", "de|Deutsch", "ja|日本語"}, "l", 3))
		}
		return
	}

	if q := u.CallbackQuery; q != nil {
		b.bot.Request(tgbotapi.NewCallback(q.ID, ""))
		d := strings.Split(q.Data, "|")
		switch d[0] {
		case "l":
			b.db.Exec("UPDATE users SET lang = ? WHERE user_id = ?", d[1], i)
			b.send(c, b.t(d[1], "y"), b.kb(r(1385, 1340), "y", 4))
		case "r":
			b.db.Exec("UPDATE users SET state = ?, y = NULL, m = NULL, d = NULL WHERE user_id = ?", "y", i)
			b.send(c, b.t(l, "y"), b.kb(r(1385, 1340), "y", 4))
		case "h":
			var h []struct{ Y, M, D int; T string }
			b.db.Select(&h, "SELECT y, m, d, t FROM history WHERE user_id = ?", i)
			t := b.t(l, "h") + "\n"
			for _, x := range h {
				t += fmt.Sprintf("%s/%s/%s (%s)\n", b.p(x.Y), b.p(x.M), b.p(x.D), x.T[:10])
			}
			b.send(c, t, nil)
		default:
			v, _ := strconv.Atoi(d[1])
			tx, _ := b.db.Beginx()
			defer tx.Rollback()
			switch user.State {
			case "y":
				if v < 1340 || v > 1385 {
					b.send(c, b.t(l, "e"), nil)
					return
				}
				tx.Exec("UPDATE users SET y = ?, state = ? WHERE user_id = ?", v, "m", i)
				b.send(c, b.t(l, "m"), b.kb(r(1, 12), "m", 4))
			case "m":
				if v < 1 || v > 12 {
					b.send(c, b.t(l, "e"), nil)
					return
				}
				tx.Exec("UPDATE users SET m = ?, state = ? WHERE user_id = ?", v, "d", i)
				b.send(c, b.t(l, "d"), b.kb(r(1, 31), "d", 5))
			case "d":
				if v < 1 || v > 31 || !b.vj(*user.Y, *user.M, v) {
					b.send(c, b.t(l, "e"), nil)
					return
				}
				tx.Exec("UPDATE users SET d = ?, state = ? WHERE user_id = ?", v, "x", i)
				tx.Exec("INSERT INTO history (user_id, y, m, d) VALUES (?, ?, ?, ?)", i, *user.Y, *user.M, v)
				g := b.jg(*user.Y, *user.M, v)
				tx.Exec("INSERT INTO reminders (user_id, r) VALUES (?, ?)", i, g.AddDate(1, 0, 0).Format("2006-01-02"))
				p := b.p(*user.Y) + "/" + b.p(*user.M) + "/" + b.p(v)
				b.send(c, fmt.Sprintf(b.t(l, "i"), p, g.Format("2006-01-02"), b.api("hijri", g, func(d map[string]interface{}) string {
					h := d["data"].(map[string]interface{})["hijri"].(map[string]interface{})
					return fmt.Sprintf("%s %s %s", h["day"], h["month"].(map[string]interface{})["en"], h["year"])
				}), int(time.Since(g).Hours()/24/365), b.z(g), b.api("holiday", g, func(d map[string]interface{}) string {
					h := d["response"].(map[string]interface{})["holidays"].([]interface{})
					if len(h) > 0 {
						return h[0].(map[string]interface{})["name"].(string)
					}
					return "No holiday"
				})), nil)
				b.sendPhoto(c, b.moon(g), b.t(l, "p"))
				b.send(c, b.t(l, "s"), b.kb([]string{"Twitter|https://twitter.com/intent/tweet?text=" + g.Format("2006-01-02"), "Instagram|https://instagram.com/stories?date=" + g.Format("2006-01-02"), b.t(l, "r") + "|r", b.t(l, "h") + "|h"}, "s", 2))
			}
			tx.Commit()
		}
	}
}

func (b *Bot) t(l, k string, v ...interface{}) string {
	return fmt.Sprintf(b.lang[l][k], v...)
}

func (b *Bot) kb(items []string, p string, r int) tgbotapi.InlineKeyboardMarkup {
	var btns []tgbotapi.InlineKeyboardButton
	for _, i := range items {
		s := strings.Split(i, "|")
		t, d := s[0], s[0]
		if len(s) > 1 {
			t, d = s[1], s[0]
		}
		if p == "y" || p == "m" || p == "d" {
			t = b.p(func() int { x, _ := strconv.Atoi(t); return x }())
		}
		btns = append(btns, tgbotapi.NewInlineKeyboardButtonData(t, fmt.Sprintf("%s|%s", p, d)))
	}
	rows := [][]tgbotapi.InlineKeyboardButton{}
	for i := 0; i < len(btns); i += r {
		e := i + r
		if e > len(btns) {
			e = len(btns)
		}
		rows = append(rows, btns[i:e])
	}
	return tgbotapi.NewInlineKeyboardMarkup(rows...)
}

func (b *Bot) p(n int) string {
	return strings.NewReplacer("0", "۰", "1", "۱", "2", "۲", "3", "۳", "4", "۴", "5", "۵", "6", "۶", "7", "۷", "8", "۸", "9", "۹").Replace(strconv.Itoa(n))
}

func (b *Bot) vj(y, m, d int) bool {
	return !(m > 12 || d > 31 || y < 1340 || y > 1385 || (m > 6 && d > 30) || (m == 12 && d == 30 && (y%4 == 3 || y%4 == 2)))
}

func (b *Bot) jg(y, m, d int) time.Time {
	jd := y*365 + y/4 + m*30 + d - 428
	if m > 6 {
		jd -= 6
	}
	gd := jd + 226899
	return time.Date(gd/365, time.Month((gd%365)/30+1), (gd%365)%30+1, 0, 0, 0, 0, time.UTC)
}

func (b *Bot) api(t string, d time.Time, f func(map[string]interface{}) string) string {
	k := fmt.Sprintf("%s_%s", t, d.Format("2006-01-02"))
	for _, c := range b.cache {
		if c.k == k && time.Since(c.t).Hours() < 24 {
			return c.v
		}
	}
	u := map[string]string{
		"hijri":   fmt.Sprintf("https://api.aladhan.com/v1/gToH?date=%s", d.Format("02-01-2006")),
		"holiday": fmt.Sprintf("https://calendarific.com/api/v2/holidays_BC_4?api_key=%s&country=IR&year=%d&month=%d&day=%d", os.Getenv("CALENDARIFIC_API_KEY"), d.Year(), d.Month(), d.Day()),
	}
	resp, _ := http.Get(u[t])
	var data map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&data)
	resp.Body.Close()
	v := f(data)
	b.cache = append(b.cache, struct{ k, v string; t time.Time }{k, v, time.Now()})
	return v
}

func (b *Bot) z(t time.Time) string {
	m, d := int(t.Month()), t.Day()
	z := []struct{ s, e int; m1, m2 int; n string }{
		{21, 19, 3, 4, "Aries"}, {20, 20, 4, 5, "Taurus"}, {21, 20, 5, 6, "Gemini"}, {21, 22, 6, 7, "Cancer"},
		{23, 22, 7, 8, "Leo"}, {23, 22, 8, 9, "Virgo"}, {23, 22, 9, 10, "Libra"}, {23, 21, 10, 11, "Scorpio"},
		{22, 21, 11, 12, "Sagittarius"}, {22, 19, 12, 1, "Capricorn"}, {20, 18, 1, 2, "Aquarius"}, {19, 20, 2, 3, "Pisces"},
	}
	for _, x := range z {
		if (m == x.m1 && d >= x.s) || (m == x.m2 && d <= x.e) {
			return x.n
		}
	}
	return "Pisces"
}

func (b *Bot) moon(t time.Time) string {
	k := fmt.Sprintf("moon_%s", t.Format("2006-01-02"))
	for _, c := range b.cache {
		if c.k == k && time.Since(c.t).Hours() < 24 {
			return c.v
		}
	}
	resp, _ := http.Get(fmt.Sprintf("https://api.nasa.gov/planetary/apod?api_key=%s&date=%s", os.Getenv("NASA_API_KEY"), t.Format("2006-01-02")))
	var d struct{ URL string }
	json.NewDecoder(resp.Body).Decode(&d)
	resp.Body.Close()
	imgResp, _ := http.Get(d.URL)
	img, _ := jpeg.Decode(imgResp.Body)
	imgResp.Body.Close()
	wm, _ := gg.LoadPNG("watermark.png")
	dc := gg.NewContext(img.Bounds().Dx(), img.Bounds().Dy())
	dc.DrawImage(img, 0, 0)
	dc.DrawImage(wm, img.Bounds().Dx()-wm.Bounds().Dx()-10, img.Bounds().Dy()-wm.Bounds().Dy()-10)
	f, _ := os.CreateTemp("", "moon_*.jpg")
	var buf bytes.Buffer
	dc.Encode(&buf, img)
	f.Write(buf.Bytes())
	f.Close()
	b.cache = append(b.cache, struct{ k, v string; t time.Time }{k, f.Name(), time.Now()})
	return f.Name()
}

func (b *Bot) send(c int64, t string, k tgbotapi.InlineKeyboardMarkup) {
	m := tgbotapi.NewMessage(c, t)
	if k != (tgbotapi.InlineKeyboardMarkup{}) {
		m.ReplyMarkup = k
	}
	b.bot.Send(m)
}

func (b *Bot) sendPhoto(c int64, p, t string) {
	photo := tgbotapi.NewPhoto(c, tgbotapi.FilePath(p))
	photo.Caption = t
	b.bot.Send(photo)
}

func r(s, e int) []string {
	r := make([]string, e-s+1)
	for i := range r {
		r[i] = strconv.Itoa(s + i)
	}
	return r
}