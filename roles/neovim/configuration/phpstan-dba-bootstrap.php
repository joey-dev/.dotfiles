<?php

use staabm\PHPStanDba\QueryReflection\RuntimeConfiguration;
use staabm\PHPStanDba\QueryReflection\QueryReflection;
use staabm\PHPStanDba\QueryReflection\PdoQueryReflector;

require_once __DIR__ . '/vendor/autoload.php';

$config = new RuntimeConfiguration();
// Enable this if you want it to also check UPDATE/INSERT/DELETE queries
$config->analyzeWriteQueries(true); 

// Connect to your local Dev database
// UPDATE THESE CREDENTIALS TO MATCH YOUR DOCKER SETUP
$pdo = new PDO(
    'mysql:dbname=add_the_database_name_here;host=127.0.0.1;port=3306',
    'root',
    'password'
);

// Boot up the DBA engine
$reflector = new PdoQueryReflector($pdo);
QueryReflection::setupReflector($reflector, $config);
