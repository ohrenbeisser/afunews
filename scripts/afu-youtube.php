<?php
/**
 * afu-youtube.php
 *
 * Listet neue YouTube-Videos der letzten 7 Tage aus den Kanälen in
 * afu-youtube-canel.json und schreibt sie nach afu-youtube.json.
 *
 * Quelle: öffentliche RSS-Feeds der Kanäle (kein API-Key nötig).
 *
 * Aufruf:
 *   CLI:  php afu-youtube.php        -> holt immer neu, schreibt die JSON
 *   Web:  afu-youtube.php            -> nutzt die JSON als Cache (1 Stunde)
 *         afu-youtube.php?json=1     -> gibt die JSON aus
 */

declare(strict_types=1);

const TAGE           = 7;
const CACHE_SEKUNDEN = 3600;
const KANAL_DATEI    = __DIR__ . '/afu-youtube-canel.json';
const AUSGABE        = __DIR__ . '/afu-youtube.json';

date_default_timezone_set('Europe/Berlin');

function h(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function holeUrl(string $url): ?string
{
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT        => 15,
            CURLOPT_USERAGENT      => 'afu-youtube/1.0',
        ]);
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);
        return ($body !== false && $code === 200) ? (string) $body : null;
    }

    $ctx  = stream_context_create(['http' => ['timeout' => 15, 'user_agent' => 'afu-youtube/1.0']]);
    $body = @file_get_contents($url, false, $ctx);
    return $body === false ? null : $body;
}

/** @return array{videos: list<array<string,string>>, statistik: list<array{Kanal:string,Anzahl:int,Fehler:bool}>, fehler: list<string>} */
function sammleVideos(): array
{
    $kanaele = json_decode((string) @file_get_contents(KANAL_DATEI), true);
    if (!is_array($kanaele)) {
        return ['videos' => [], 'statistik' => [], 'fehler' => ['Kanalliste ' . basename(KANAL_DATEI) . ' nicht lesbar']];
    }

    $grenze = time() - TAGE * 86400;
    $videos = [];
    $fehler = [];
    $stat   = [];

    foreach ($kanaele as $k) {
        $id   = (string) ($k['kanal_id'] ?? '');
        $name = (string) ($k['kanal'] ?? $id);
        if (!preg_match('/^[A-Za-z0-9_-]{20,30}$/', $id)) {
            $fehler[] = "$name: ungültige Kanal-ID";
            $stat[] = ['Kanal' => $name, 'Anzahl' => 0, 'Fehler' => true];
            continue;
        }

        $xml  = holeUrl('https://www.youtube.com/feeds/videos.xml?channel_id=' . $id);
        $feed = $xml !== null ? @simplexml_load_string($xml) : false;
        if ($feed === false) {
            $fehler[] = "$name: Feed nicht abrufbar";
            $stat[] = ['Kanal' => $name, 'Anzahl' => 0, 'Fehler' => true];
            continue;
        }

        $anzahl = 0;
        foreach ($feed->entry as $e) {
            $zeit = strtotime((string) $e->published);
            if ($zeit === false || $zeit < $grenze) {
                continue;
            }
            $media = $e->children('http://search.yahoo.com/mrss/');
            $videos[] = [
                'Titel'  => trim((string) $e->title),
                'Kanal'  => $name,
                'Datum'  => date('c', $zeit),
                'Inhalt' => trim((string) $media->group->description),
                'Link'   => (string) $e->link['href'],
            ];
            $anzahl++;
        }
        $stat[] = ['Kanal' => $name, 'Anzahl' => $anzahl, 'Fehler' => false];
    }

    usort($videos, fn ($a, $b) => strcmp($b['Datum'], $a['Datum']));
    return ['videos' => $videos, 'statistik' => $stat, 'fehler' => $fehler];
}

/** Rahmen der JSON-Datei: Einträge plus Statistik pro Kanal. */
function baueDaten(array $eintraege, array $statistik): array
{
    return [
        'Eintraege' => $eintraege,
        'Statistik' => [
            'Stand'        => date('c'),
            'Zeitraum_Tage' => TAGE,
            'Gesamt'       => count($eintraege),
            'Kanaele'      => array_map(
                fn ($s) => ['Kanal' => $s['Kanal'], 'Anzahl' => $s['Anzahl']],
                $statistik
            ),
        ],
    ];
}

function schreibeJson(array $daten): bool
{
    $json = json_encode($daten, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        return false;
    }
    $tmp = AUSGABE . '.tmp';
    return @file_put_contents($tmp, $json . "\n") !== false && @rename($tmp, AUSGABE);
}

/** Liest die JSON-Datei; null, wenn sie fehlt oder das alte Format hat. */
function leseCache(): ?array
{
    $daten = json_decode((string) @file_get_contents(AUSGABE), true);
    return is_array($daten) && isset($daten['Eintraege'], $daten['Statistik']['Kanaele']) ? $daten : null;
}

// --- Daten besorgen -------------------------------------------------------
$cli    = PHP_SAPI === 'cli';
$fehler = [];
$cache  = !$cli && is_file(AUSGABE) && (time() - filemtime(AUSGABE)) < CACHE_SEKUNDEN ? leseCache() : null;

if ($cache !== null) {
    $videos     = $cache['Eintraege'];
    $statistik = $cache['Statistik']['Kanaele'];
} else {
    ['videos' => $videos, 'statistik' => $statistik, 'fehler' => $fehler] = sammleVideos();
    // Nur schreiben, wenn kein Kanal ausgefallen ist, sonst gehen Einträge verloren
    if ($fehler === [] && !schreibeJson(baueDaten($videos, $statistik))) {
        $fehler[] = 'Schreiben von ' . basename(AUSGABE) . ' fehlgeschlagen';
    }
}

// --- Ausgabe --------------------------------------------------------------
if ($cli) {
    foreach ($videos as $v) {
        echo date('d.m.Y', strtotime($v['Datum'])), '  ', $v['Kanal'], '  ', $v['Titel'], "\n";
    }

    echo "\nStatistik der letzten ", TAGE, " Tage:\n";
    $breite = max(array_map(fn ($s) => mb_strlen($s['Kanal']), $statistik) ?: [0]);
    foreach ($statistik as $s) {
        $anzahl = $s['Fehler'] ?? false ? 'Fehler' : (string) $s['Anzahl'];
        echo '  ', $s['Kanal'], str_repeat(' ', $breite - mb_strlen($s['Kanal'])), '  ', $anzahl, "\n";
    }
    echo '  Gesamt: ', count($videos), "\n";

    foreach ($fehler as $f) {
        fwrite(STDERR, "Fehler: $f\n");
    }
    exit($fehler === [] ? 0 : 1);
}

if (isset($_GET['json'])) {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(baueDaten($videos, $statistik), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
?>
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Afu – neue YouTube-Videos</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 50rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
        article { border-bottom: 1px solid #ddd; padding: 1rem 0; }
        h2 { font-size: 1.1rem; margin: 0 0 .25rem; }
        .meta { color: #666; font-size: .9rem; margin-bottom: .5rem; }
        .fehler { background: #fee; padding: .5rem 1rem; }
        table { border-collapse: collapse; }
        td, th { padding: .2rem 1rem .2rem 0; text-align: left; }
    </style>
</head>
<body>
    <h1>Neue Videos der letzten <?= TAGE ?> Tage</h1>

    <?php if ($fehler): ?>
        <div class="fehler"><?php foreach ($fehler as $f): ?><p><?= h($f) ?></p><?php endforeach; ?></div>
    <?php endif; ?>

    <?php if (!$videos): ?>
        <p>Keine neuen Videos.</p>
    <?php endif; ?>

    <?php foreach ($videos as $v): ?>
        <article>
            <h2><a href="<?= h($v['Link'] ?? '#') ?>" rel="noopener"><?= h($v['Titel']) ?></a></h2>
            <div class="meta"><?= h($v['Kanal']) ?> · <?= h(date('d.m.Y', strtotime($v['Datum']))) ?></div>
            <p><?= nl2br(h(mb_strimwidth($v['Inhalt'], 0, 300, '…'))) ?></p>
        </article>
    <?php endforeach; ?>

    <h2>Statistik</h2>
    <table>
        <?php foreach ($statistik as $s): ?>
            <tr><td><?= h($s['Kanal']) ?></td><td><?= ($s['Fehler'] ?? false) ? 'Fehler' : (int) $s['Anzahl'] ?></td></tr>
        <?php endforeach; ?>
        <tr><th>Gesamt</th><th><?= count($videos) ?></th></tr>
    </table>
</body>
</html>
