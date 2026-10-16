<?php

// Shared phpstan-dba bootstrap. Each project sets its own database in `.envrc`:
//   export PHPSTAN_DBA_URL="mysql://user:password@127.0.0.1:3306/database"
// Without PHPSTAN_DBA_URL the query checks are skipped.

use staabm\PHPStanDba\QueryReflection\ChainedReflector;
use staabm\PHPStanDba\QueryReflection\PdoQueryReflector;
use staabm\PHPStanDba\QueryReflection\QueryReflection;
use staabm\PHPStanDba\QueryReflection\RuntimeConfiguration;

require_once '@composerHome@/vendor/autoload.php';

$config = new RuntimeConfiguration();
// Also check UPDATE/INSERT/DELETE queries (through EXPLAIN, so nothing is changed)
$config->analyzeWriteQueries(true);

$url = getenv('PHPSTAN_DBA_URL');

if ($url === false || $url === '') {
    // phpstan-dba needs a reflector; an empty chain knows no queries, so it reports nothing
    QueryReflection::setupReflector(new ChainedReflector(), $config);

    return;
}

$parts = parse_url($url);

if ($parts === false || !isset($parts['host'], $parts['path'])) {
    throw new RuntimeException('PHPSTAN_DBA_URL must look like mysql://user:password@host:port/database');
}

$pdo = new PDO(
    sprintf(
        'mysql:dbname=%s;host=%s;port=%d',
        ltrim($parts['path'], '/'),
        $parts['host'],
        $parts['port'] ?? 3306,
    ),
    urldecode($parts['user'] ?? 'root'),
    urldecode($parts['pass'] ?? ''),
);

QueryReflection::setupReflector(new PdoQueryReflector($pdo), $config);
