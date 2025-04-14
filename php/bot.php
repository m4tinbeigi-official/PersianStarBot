<?php
// php/bot.php
use App\Http\Controllers\BotController;
use Illuminate\Support\Facades\Route;

Route::post('/telegram/webhook', [BotController::class, 'handle'])->middleware('throttle:60,1');

// app/Traits/BotLogic.php
namespace App\Traits;

use Carbon\Carbon;
use Morilog\Jalali\Jalalian;
use Telegram\Bot\Keyboard\Keyboard;

trait BotLogic {
    private function t(string $key, array $params = []): string {
        return __($key, $params);
    }

    private function k(array $items, string $p, int $r = 4): Keyboard {
        return Keyboard::make()->inline()->row(...array_chunk(array_map(
            fn($i) => Keyboard::inlineButton(['text' => strtr($i, array_combine(range(0, 9), ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']))), 'callback_data' => "$p|$i"]),
            $items), $r)[0] ?? $items));
    }

    private function sk(string $d): Keyboard {
        return Keyboard::make()->inline()->row(
            Keyboard::inlineButton(['text' => __('share_twitter'), 'url' => "https://twitter.com/intent/tweet?text=$d"]),
            Keyboard::inlineButton(['text' => __('share_instagram'), 'url' => "https://instagram.com/stories?date=$d"])
        )->row(
            Keyboard::inlineButton(['text' => __('reset'), 'callback_data' => 'r']),
            Keyboard::inlineButton(['text' => __('history'), 'callback_data' => 'h'])
        );
    }

    private function lk(): Keyboard {
        $l = ['en' => 'English', 'es' => 'Español', 'zh' => '中文', 'hi' => 'हिन्दी', 'ar' => 'العربية', 'pt' => 'Português', 'ru' => 'Русский', 'fr' => 'Français', 'de' => 'Deutsch', 'ja' => '日本語'];
        return Keyboard::make()->inline()->row(...array_map(fn($c, $n) => Keyboard::inlineButton(['text' => $n, 'callback_data' => "l|$c"]), array_keys($l), $l));
    }

    private function hijri(string $d): string {
        return cache()->remember("hijri_$d", 86400, fn() => with(json_decode(file_get_contents("https://api.aladhan.com/v1/gToH?date=$d"), true)['data']['hijri'], fn($h) => "$h[day] $h[month][en] $h[year]"));
    }

    private function zodiac(string $d): string {
        $c = Carbon::parse($d);
        return match (true) {
            ($c->month == 3 && $c->day >= 21) || ($c->month == 4 && $c->day <= 19) => 'Aries',
            ($c->month == 4 && $c->day >= 20) || ($c->month == 5 && $c->day <= 20) => 'Taurus',
            ($c->month == 5 && $c->day >= 21) || ($c->month == 6 && $c->day <= 20) => 'Gemini',
            ($c->month == 6 && $c->day >= 21) || ($c->month == 7 && $c->day <= 22) => 'Cancer',
            ($c->month == 7 && $c->day >= 23) || ($c->month == 8 && $c->day <= 22) => 'Leo',
            ($c->month == 8 && $c->day >= 23) || ($c->month == 9 && $c->day <= 22) => 'Virgo',
            ($c->month == 9 && $c->day >= 23) || ($c->month == 10 && $c->day <= 22) => 'Libra',
            ($c->month == 10 && $c->day >= 23) || ($c->month == 11 && $c->day <= 21) => 'Scorpio',
            ($c->month == 11 && $c->day >= 22) || ($c->month == 12 && $c->day <= 21) => 'Sagittarius',
            ($c->month == 12 && $c->day >= 22) || ($c->month == 1 && $c->day <= 19) => 'Capricorn',
            ($c->month == 1 && $c->day >= 20) || ($c->month == 2 && $c->day <= 18) => 'Aquarius',
            default => 'Pisces'
        };
    }

    private function holiday(string $d): string {
        $c = Carbon::parse($d);
        return cache()->remember("holiday_$d", 86400, fn() => json_decode(file_get_contents("https://calendarific.com/api/v2/holidays?api_key=" . env('CALENDARIFIC_API_KEY') . "&country=IR&year={$c->year}&month={$c->month}&day={$c->day}"), true)['response']['holidays'][0]['name'] ?? 'No holiday');
    }

    private function moon(string $d): \Telegram\Bot\FileUpload\InputFile {
        if ($f = cache()->get("moon_$d")) return new \Telegram\Bot\FileUpload\InputFile($f, 'moon.jpg');
        $u = json_decode(file_get_contents("https://api.nasa.gov/planetary/apod?api_key=" . env('NASA_API_KEY') . "&date=$d"), true)['url'];
        $t = tempnam(sys_get_temp_dir(), 'moon');
        file_put_contents($t, file_get_contents($u));
        $i = imagecreatefromjpeg($t);
        $w = imagecreatefrompng(public_path('watermark.png'));
        imagecopy($i, $w, imagesx($i) - imagesx($w) - 10, imagesy($i) - imagesy($w) - 10, 0, 0, imagesx($w), imagesy($w));
        $f = tempnam(sys_get_temp_dir(), 'moon_final');
        imagejpeg($i, $f, 85);
        imagedestroy($i);
        imagedestroy($w);
        unlink($t);
        cache()->put("moon_$d", $f, 86400);
        return new \Telegram\Bot\FileUpload\InputFile($f, 'moon.jpg');
    }
}

// app/Models/User.php
namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class User extends Model {
    use HasFactory;
    protected $guarded = [], $primaryKey = 'user_id';
    public $incrementing = false;
    public function history() { return $this->hasMany(BirthHistory::class, 'user_id'); }
    public function reminders() { return $this->hasMany(Reminder::class, 'user_id'); }
}

// app/Models/BirthHistory.php
namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class BirthHistory extends Model {
    use HasFactory;
    protected $guarded = [];
}

// app/Models/Reminder.php
namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Reminder extends Model {
    use HasFactory;
    protected $guarded = [];
}

// app/Http/Controllers/BotController.php
namespace App\Http\Controllers;

use App\Models\User;
use App\Traits\BotLogic;
use Illuminate\Support\Facades\DB;
use Morilog\Jalali\Jalalian;
use Telegram\Bot\Api;
use Throwable;

class BotController extends Controller {
    use BotLogic;
    private Api $telegram;

    public function __construct(Api $telegram) {
        $this->telegram = $telegram;
    }

    public function handle() {
        $u = $this->telegram->getWebhookUpdate();
        $c = $u->getMessage()?->chat->id ?? $u->getCallbackQuery()?->message->chat->id;
        $i = $u->getMessage()?->from->id ?? $u->getCallbackQuery()?->from->id;
        $l = User::where('user_id', $i)->first()?->language ?? ($u->getMessage()?->from->language_code && in_array($u->getMessage()->from->language_code, ['en', 'fa', 'es', 'zh', 'hi', 'ar', 'pt', 'ru', 'fr', 'de', 'ja']) ? $u->getMessage()->from->language_code : 'en');

        try {
            DB::beginTransaction();
            app()->setLocale($l);

            if ($t = $u->getMessage()?->text) {
                if ($t == '/start') {
                    $user = User::updateOrCreate(['user_id' => $i], ['chat_id' => $c, 'state' => 'y', 'language' => $l]);
                    $user->update(['birth_year' => null, 'birth_month' => null, 'birth_day' => null]);
                    return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('y'), 'reply_markup' => $this->k(range(1385, 1340), 'y')]);
                }
                if ($t == '/language') {
                    return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('l'), 'reply_markup' => $this->lk()]);
                }
            }

            if ($q = $u->getCallbackQuery()) {
                $d = explode('|', $q->data);
                $user = User::where('user_id', $i)->firstOrFail();

                if ($d[0] == 'l') {
                    $user->update(['language' => $d[1]]);
                    return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('y'), 'reply_markup' => $this->k(range(1385, 1340), 'y')]);
                }

                if ($d[0] == 'r') {
                    $user->update(['state' => 'y', 'birth_year' => null, 'birth_month' => null, 'birth_day' => null]);
                    return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('y'), 'reply_markup' => $this->k(range(1385, 1340), 'y')]);
                }

                if ($d[0] == 'h') {
                    $h = $user->history->map(fn($x) => strtr("{$x->birth_year}/{$x->birth_month}/{$x->birth_day} ({$x->created_at})", array_combine(range(0, 9), ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'])))->join("\n") ?: $this->t('n');
                    return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('h') . "\n$h"]);
                }

                $v = (int)$d[1];
                switch ($user->state) {
                    case 'y':
                        abort_unless($v >= 1340 && $v <= 1385, 400, 'Invalid year');
                        $user->update(['birth_year' => $v, 'state' => 'm']);
                        $r = $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('m'), 'reply_markup' => $this->k(range(1, 12), 'm')]);
                        break;
                    case 'm':
                        abort_unless($v >= 1 && $v <= 12, 400, 'Invalid month');
                        $user->update(['birth_month' => $v, 'state' => 'd']);
                        $r = $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('d'), 'reply_markup' => $this->k(range(1, 31), 'd', 5)]);
                        break;
                    case 'd':
                        abort_unless($v >= 1 && $v <= 31 && Jalalian::forge("{$user->birth_year}/{$user->birth_month}/$v")->isValid(), 400, 'Invalid day');
                        $user->update(['birth_day' => $v, 'state' => 'x']);
                        $user->history()->create(['birth_year' => $user->birth_year, 'birth_month' => $user->birth_month, 'birth_day' => $v]);
                        $g = Jalalian::forge("{$user->birth_year}/{$user->birth_month}/$v")->toCarbon()->format('Y-m-d');
                        $user->reminders()->create(['reminder_date' => Carbon::parse($g)->addYear()->format('Y-m-d')]);
                        $p = strtr("{$user->birth_year}/{$user->birth_month}/{$user->birth_day}", array_combine(range(0, 9), ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'])));
                        $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('i', ['persian' => $p, 'gregorian' => $g, 'hijri' => $this->hijri($g), 'age' => Carbon::parse($g)->age, 'zodiac' => $this->zodiac($g), 'holiday' => $this->holiday($g)])]);
                        $this->telegram->sendPhoto(['chat_id' => $c, 'photo' => $this->moon($g), 'caption' => $this->t('p')]);
                        $r = $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('s'), 'reply_markup' => $this->sk($g)]);
                        break;
                }
                DB::commit();
                return $r;
            }
        } catch (Throwable $e) {
            DB::rollBack();
            \Log::error($e->getMessage());
            return $this->telegram->sendMessage(['chat_id' => $c, 'text' => $this->t('e')]);
        }
    }
}

// database/migrations/2025_04_13_000001_create_tables.php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void {
        Schema::create('users', function (Blueprint $t) {
            $t->bigInteger('user_id')->primary();
            $t->bigInteger('chat_id');
            $t->string('state', 50);
            $t->string('lang', 5)->default('en');
            $t->integer('y')->nullable();
            $t->integer('m')->nullable();
            $t->integer('d')->nullable();
            $t->timestamps();
        });

        Schema::create('birth_history', function (Blueprint $t) {
            $t->id();
            $t->bigInteger('user_id');
            $t->integer('y');
            $t->integer('m');
            $t->integer('d');
            $t->timestamps();
        });

        Schema::create('reminders', function (Blueprint $t) {
            $t->id();
            $t->bigInteger('user_id');
            $t->date('r');
            $t->timestamps();
        });
    }

    public function down(): void {
        Schema::dropIfExists('users');
        Schema::dropIfExists('birth_history');
        Schema::dropIfExists('reminders');
    }
};

// resources/lang/en.json
{"y":"Select birth year:","m":"Select birth month:","d":"Select birth day:","i":"📅 Info:\nPersian: :persian\nGregorian: :gregorian\nHijri: :hijri\nAge: :age\nZodiac: :zodiac\nHoliday: :holiday","e":"Invalid input.","p":"Moon phase","s":"Share or reset:","share_twitter":"Share on Twitter","share_instagram":"Share on Instagram","r":"Reset","h":"View history","n":"No history found","l":"Select language:"}

// resources/lang/fa.json
{"y":"سال تولد:","m":"ماه تولد:","d":"روز تولد:","i":"📅 اطلاعات:\nشمسی: :persian\nمیلادی: :gregorian\nقمری: :hijri\nسن: :age\nزودیاک: :zodiac\nتعطیلات: :holiday","e":"ورودی نامعتبر.","p":"فاز ماه","s":"اشتراک یا شروع مجدد:","share_twitter":"اشتراک در توییتر","share_instagram":"اشتراک در اینستاگرام","r":"شروع مجدد","h":"مشاهده تاریخچه","n":"تاریخچه‌ای یافت نشد","l":"انتخاب زبان:"}