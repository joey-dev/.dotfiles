<?php

namespace Doctrine\DBAL;

use Closure;
use Doctrine\DBAL\Cache\CacheException;
use Doctrine\DBAL\Cache\QueryCacheProfile;
use Doctrine\DBAL\Driver\Connection as DriverConnection;
use Doctrine\DBAL\Types\Type;
use Throwable;
use Traversable;

class Connection implements DriverConnection
{
    /**
     * Prepares and executes an SQL query and returns the first row of the result
     * as an associative array.
     *
     * @deprecated Use fetchAssociative()
     *
     * @param string                                                               $sql    SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<string, string>|false False is returned if no rows are found.
     *
     * @throws Exception
     */
    public function fetchAssoc($sql, array $params = [], array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the first row of the result
     * as a numerically indexed array.
     *
     * @deprecated Use fetchNumeric()
     *
     * @param string                                                               $sql    SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<int, string>|false False is returned if no rows are found.
     */
    public function fetchArray($sql, array $params = [], array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the value of a single column
     * of the first row of the result.
     *
     * @deprecated Use fetchOne() instead.
     *
     * @param string                                                               $sql    SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param int                                                                  $column 0-indexed column number
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return string|false False is returned if no rows are found.
     *
     * @throws Exception
     */
    public function fetchColumn($sql, array $params = [], $column = 0, array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the first row of the result
     * as an associative array.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string|int|null>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|null> $types  Parameter types
     *
     * @return array<string, string>|false False is returned if no rows are found.
     *
     * @throws Exception
     */
    public function fetchAssociative(string $query, array $params = [], array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the first row of the result
     * as a numerically indexed array.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<int, string>|false False is returned if no rows are found.
     *
     * @throws Exception
     */
    public function fetchNumeric(string $query, array $params = [], array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the value of a single column
     * of the first row of the result.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return string|false False is returned if no rows are found.
     *
     * @throws Exception
     */
    public function fetchOne(string $query, array $params = [], array $types = [])
    {
    }

    /**
     * Adds condition based on the criteria to the query components
     *
     * @param array<string,string> $criteria   Map of key columns to their values
     * @param string[]            $columns    Column names
     * @param string[]             $values     Column values
     * @param string[]            $conditions Key conditions
     *
     * @throws Exception
     */
    private function addCriteriaCondition(
        array $criteria,
        array &$columns,
        array &$values,
        array &$conditions
    ): void {
    }

    /**
     * Executes an SQL DELETE statement on a table.
     *
     * Table expression and columns are not escaped and are not safe for user-input.
     *
     * @param string                                                               $table    Table name
     * @param array<string, string>                                                 $criteria Deletion criteria
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types    Parameter types
     *
     * @return int|string The number of affected rows.
     *
     * @throws Exception
     */
    public function delete($table, array $criteria, array $types = [])
    {
    }

    /**
     * Executes an SQL UPDATE statement on a table.
     *
     * Table expression and columns are not escaped and are not safe for user-input.
     *
     * @param string                                                               $table    Table name
     * @param array<string, string>                                                 $data     Column-value pairs
     * @param array<string, string>                                                 $criteria Update criteria
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types    Parameter types
     *
     * @return int|string The number of affected rows.
     *
     * @throws Exception
     */
    public function update($table, array $data, array $criteria, array $types = [])
    {
    }

    /**
     * Inserts a table row with specified data.
     *
     * Table expression and columns are not escaped and are not safe for user-input.
     *
     * @param string                                                               $table Table name
     * @param array<string, string>                                                 $data  Column-value pairs
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types Parameter types
     *
     * @return int|string The number of affected rows.
     *
     * @throws Exception
     */
    public function insert($table, array $data, array $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an associative array.
     *
     * @deprecated Use fetchAllAssociative()
     *
     * @param string         $sql    The SQL query.
     * @param array<string, int|string|array<int|null>>        $params The query parameters.
     * @param int[]|string[] $types  The query parameter types.
     *
     * @return string[]
     */
    public function fetchAll($sql, array $params = [], $types = [])
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an array of numeric arrays.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<int,array<int,string>>
     *
     * @throws Exception
     */
    public function fetchAllNumeric(string $query, array $params = [], array $types = []): array
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an array of associative arrays.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string|array>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|null> $types  Parameter types
     *
     * @return array<int,array<string,string>>
     *
     * @throws Exception
     */
    public function fetchAllAssociative(string $query, array $params = [], array $types = []): array
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an associative array with the keys
     * mapped to the first column and the values mapped to the second column.
     *
     * @param string                                           $query  SQL query
     * @param array<int, string>|array<string, string>           $params Query parameters
     * @param array<int, int|string>|array<string, int|string> $types  Parameter types
     *
     * @return array<string,string>
     *
     * @throws Exception
     */
    public function fetchAllKeyValue(string $query, array $params = [], array $types = []): array
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an associative array with the keys mapped
     * to the first column and the values being an associative array representing the rest of the columns
     * and their values.
     *
     * @param string                                           $query  SQL query
     * @param array<int, string>|array<string, string>           $params Query parameters
     * @param array<int, int|string>|array<string, int|string> $types  Parameter types
     *
     * @return array<string,array<string,string>>
     *
     * @throws Exception
     */
    public function fetchAllAssociativeIndexed(string $query, array $params = [], array $types = []): array
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an array of the first column values.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<int,string>
     *
     * @throws Exception
     */
    public function fetchFirstColumn(string $query, array $params = [], array $types = []): array
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an iterator over rows represented as numeric arrays.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return Traversable<int,array<int,string>>
     *
     * @throws Exception
     */
    public function iterateNumeric(string $query, array $params = [], array $types = []): Traversable
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an iterator over rows represented
     * as associative arrays.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return Traversable<int,array<string,string>>
     *
     * @throws Exception
     */
    public function iterateAssociative(string $query, array $params = [], array $types = []): Traversable
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an iterator with the keys
     * mapped to the first column and the values mapped to the second column.
     *
     * @param string                                           $query  SQL query
     * @param array<int, string>|array<string, string>           $params Query parameters
     * @param array<int, int|string>|array<string, int|string> $types  Parameter types
     *
     * @return Traversable<string,string>
     *
     * @throws Exception
     */
    public function iterateKeyValue(string $query, array $params = [], array $types = []): Traversable
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an iterator with the keys mapped
     * to the first column and the values being an associative array representing the rest of the columns
     * and their values.
     *
     * @param string                                           $query  SQL query
     * @param array<int, string>|array<string, string>           $params Query parameters
     * @param array<int, int|string>|array<string, int|string> $types  Parameter types
     *
     * @return Traversable<string,array<string,string>>
     *
     * @throws Exception
     */
    public function iterateAssociativeIndexed(string $query, array $params = [], array $types = []): Traversable
    {
    }

    /**
     * Prepares and executes an SQL query and returns the result as an iterator over the first column values.
     *
     * @param string                                                               $query  SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return Traversable<int,string>
     *
     * @throws Exception
     */
    public function iterateColumn(string $query, array $params = [], array $types = []): Traversable
    {
    }

    /**
     * Executes an, optionally parametrized, SQL query.
     *
     * If the query is parametrized, a prepared statement is used.
     * If an SQLLogger is configured, the execution is logged.
     *
     * @param string                                                               $sql    SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return ForwardCompatibility\DriverStatement|ForwardCompatibility\DriverResultStatement
     *
     * The executed statement or the cached result statement if a query cache profile is used
     *
     * @throws Exception
     */
    public function executeQuery($sql, array $params = [], $types = [], ?QueryCacheProfile $qcp = null)
    {
    }

    /**
     * Executes a caching query.
     *
     * @param string                                                               $sql    SQL query
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return ForwardCompatibility\DriverResultStatement
     *
     * @throws CacheException
     */
    public function executeCacheQuery($sql, $params, $types, QueryCacheProfile $qcp)
    {
    }

    /**
     * Executes an, optionally parametrized, SQL query and returns the result,
     * applying a given projection/transformation function on each row of the result.
     *
     * @deprecated
     *
     * @param string  $sql      The SQL query to execute.
     * @param string[] $params   The parameters, if any.
     * @param Closure $function The transformation function that is applied on each row.
     *                           The function receives a single parameter, an array, that
     *                           represents a row of the result set.
     *
     * @return string[] The projected result of the query.
     */
    public function project($sql, array $params, Closure $function)
    {
    }

    /**
     * Executes an SQL INSERT/UPDATE/DELETE query with the given parameters
     * and returns the number of affected rows.
     *
     * This method supports PDO binding types as well as DBAL mapping types.
     *
     * @deprecated Use {@link executeStatement()} instead.
     *
     * @param string                                                               $sql    SQL statement
     * @param array<int, string>|array<string, string>                               $params Statement parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return int|string The number of affected rows.
     *
     * @throws Exception
     */
    public function executeUpdate($sql, array $params = [], array $types = [])
    {
    }

    /**
     * Executes an SQL statement with the given parameters and returns the number of affected rows.
     *
     * Could be used for:
     *  - DML statements: INSERT, UPDATE, DELETE, etc.
     *  - DDL statements: CREATE, DROP, ALTER, etc.
     *  - DCL statements: GRANT, REVOKE, etc.
     *  - Session control statements: ALTER SESSION, SET, DECLARE, etc.
     *  - Other statements that don't yield a row set.
     *
     * This method supports PDO binding types as well as DBAL mapping types.
     *
     * @param string                                                               $sql    SQL statement
     * @param array<int, string>|array<string, string>                               $params Statement parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return int|string The number of affected rows.
     *
     * @throws Exception
     */
    public function executeStatement($sql, array $params = [], array $types = [])
    {
    }

    /**
     * Executes a function in a transaction.
     *
     * The function gets passed this Connection instance as an (optional) parameter.
     *
     * If an exception occurs during execution of the function or transaction commit,
     * the transaction is rolled back and the exception re-thrown.
     *
     * @param Closure $func The function to execute transactionally.
     *
     * @return string The value returned by $func
     *
     * @throws Throwable
     */
    public function transactional(Closure $func)
    {
    }

    /**
     * Returns the savepoint name to use for nested transactions are false if they are not supported
     * "savepointFormat" parameter is not set
     *
     * @return string A string with the savepoint name or false.
     */
    protected function _getNestedTransactionSavePointName()
    {
    }

    /**
     * Converts a given value to its database representation according to the conversion
     * rules of a specific DBAL mapping type.
     *
     * @param string  $value The value to convert.
     * @param string $type  The name of the DBAL mapping type.
     *
     * @return string The converted value.
     */
    public function convertToDatabaseValue($value, $type)
    {
    }

    /**
     * Converts a given value to its PHP representation according to the conversion
     * rules of a specific DBAL mapping type.
     *
     * @param string  $value The value to convert.
     * @param string $type  The name of the DBAL mapping type.
     *
     * @return string The converted type.
     */
    public function convertToPHPValue($value, $type)
    {
    }

    /**
     * Binds a set of parameters, some or all of which are typed with a PDO binding type
     * or DBAL mapping type, to a given statement.
     *
     * @internal Duck-typing used on the $stmt parameter to support driver statements as well as
     *           raw PDOStatement instances.
     *
     * @param \Doctrine\DBAL\Driver\Statement                                      $stmt   Prepared statement
     * @param array<int, string>|array<string, string>                               $params Statement parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return void
     */
    private function _bindTypedValues($stmt, array $params, array $types)
    {
    }

    /**
     * Gets the binding type of a given type. The given type can be a PDO or DBAL mapping type.
     *
     * @param string                $value The value to bind.
     * @param int|string|Type|null $type  The type to bind (PDO or DBAL).
     *
     * @return array{string, int} [0] => the (escaped) value, [1] => the binding type.
     */
    private function getBindingInfo($value, $type): array
    {
    }

    /**
     * Resolves the parameters to a format which can be displayed.
     *
     * @internal This is a purely internal method. If you rely on this method, you are advised to
     *           copy/paste the code as this method may change, or be removed without prior notice.
     *
     * @param array<int, string>|array<string, string>                               $params Query parameters
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types  Parameter types
     *
     * @return array<int, int|string|Type|null>|array<string, int|string|Type|null>
     */
    public function resolveParams(array $params, array $types)
    {
    }

    /**
     * @internal
     *
     * @param array<int, string>|array<string, string>                               $params
     * @param array<int, int|string|Type|null>|array<string, int|string|Type|null> $types
     *
     * @psalm-return never-return
     *
     * @throws Exception
     */
    public function handleExceptionDuringQuery(Throwable $e, string $sql, array $params = [], array $types = []): void
    {
    }
}

