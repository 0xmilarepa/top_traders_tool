

def get_evm_traders_and_connections(chain, contract_address, start_date, end_date, min_usd_amount=1, max_usd_amount=100000000, min_active_days=3, limit=200):
    """
    Get both top traders and their connections in a single query for EVM chains, excluding CEX and DEX addresses, Pools and Bridges.

    Parameters:
    chain (str): Chain name (ethereum, base, arbitrum, optimism, polygon, bsc, avalanche)
    contract_address (str): Token contract address
    start_date (str): Start date in YYYY-MM-DD format
    end_date (str): End date in YYYY-MM-DD format
    min_usd_amount (float): Minimum USD amount for trades to be considered
    max_usd_amount (float): Maximum USD amount for trades to be considered
    min_active_days (int): Minimum number of different days with trading activity
    limit (int): Number of top traders to return
    """
    print("📦 Preparing query for:")
    print(f"🔗 Chain: {chain}")
    print(f"🪙 Contract Address: {contract_address}")
    print(f"📅 Date Range: {start_date} to {end_date}")
    print(f"💰 USD Amount Range: {min_usd_amount} to {max_usd_amount}")
    print(f"📊 Minimum Active Days: {min_active_days}")
    print(f"🏆 Top Traders Limit: {limit}")
    print("-" * 60)

    valid_chains = ['ethereum', 'base', 'arbitrum', 'optimism', 'avalanche', 'bsc', 'polygon']
    chain = chain.lower()

    if chain not in valid_chains:
        raise ValueError(f"Chain must be one of {valid_chains}")

    evm_query = f"""
    WITH swap_transactions AS (
        SELECT
            block_timestamp,
            tx_hash,
            sender as trader,
            COALESCE(amount_in_usd, 0) + COALESCE(amount_out_usd, 0) as amount_usd,
            CASE
                WHEN token_in = LOWER(TRIM('{contract_address}')) THEN amount_in
                WHEN token_out = LOWER(TRIM('{contract_address}')) THEN amount_out
            END as token_amount
        FROM {chain}.defi.ez_dex_swaps
        WHERE (token_in = LOWER(TRIM('{contract_address}')) OR token_out = LOWER(TRIM('{contract_address}')))
            AND block_timestamp >= '{start_date}'
            AND block_timestamp < DATEADD(day, 1, '{end_date}')::date
            AND COALESCE(amount_in_usd, 0) + COALESCE(amount_out_usd, 0) >= {min_usd_amount}
            AND COALESCE(amount_in_usd, 0) + COALESCE(amount_out_usd, 0) <= {max_usd_amount}
    ),

    filtered_traders AS (
        SELECT DISTINCT
            trader as address
        FROM swap_transactions
        WHERE trader NOT IN (
            SELECT address
            FROM {chain}.core.dim_labels
            WHERE label_type IN (
                'cex', 'dex', 'defi', 'bridge', 'contract', 'treasury', 'infrastructure'
            )
            OR label_subtype IN (
                'pool', 'router', 'exchange', 'mev_bot', 'flash_loan', 'vault',
                'wrapper', 'burn_address', 'null_address'
            )
            OR LOWER(address_name) LIKE ANY (
                '%pool%', '%bot%', '%mev%', '%vault%', '%treasury%',
                '%wrapper%', '%flash%loan%', '%token%account%', '%amm%'
            )
            LIMIT 1000
        )
    ),

    trading_patterns AS (
        SELECT
            trader as address,
            COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) as active_days,
            COUNT(DISTINCT tx_hash) as total_trades,
            COUNT(DISTINCT tx_hash)::FLOAT / COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) as avg_daily_trades,
            SUM(amount_usd) as total_volume
        FROM swap_transactions
        WHERE trader IN (SELECT address FROM filtered_traders)
        GROUP BY trader
        HAVING
            COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) >= {min_active_days}
            AND COUNT(DISTINCT tx_hash) >= 5
    ),

    top_traders AS (
        SELECT
            s.trader as address,
            COUNT(DISTINCT s.tx_hash) as trade_count,
            SUM(ABS(s.token_amount)) as total_tokens_traded,
            SUM(s.amount_usd) as total_usd_traded,
            tp.active_days,
            tp.avg_daily_trades
        FROM swap_transactions s
        JOIN trading_patterns tp ON s.trader = tp.address
        WHERE s.trader IN (SELECT address FROM filtered_traders)
        GROUP BY s.trader, tp.active_days, tp.avg_daily_trades
        HAVING total_usd_traded > 0
        QUALIFY ROW_NUMBER() OVER (ORDER BY total_usd_traded DESC) <= {limit}
    ),

    connections AS (
        SELECT
            s1.trader as source,
            s2.trader as target,
            COUNT(DISTINCT s1.tx_hash) as transaction_count,
            SUM(ABS(s1.token_amount)) as total_tokens,
            SUM(s1.amount_usd) as total_value
        FROM swap_transactions s1
        JOIN swap_transactions s2
            ON s1.tx_hash = s2.tx_hash
            AND s1.trader < s2.trader
        WHERE s1.trader IN (SELECT address FROM top_traders)
            AND s2.trader IN (SELECT address FROM top_traders)
        GROUP BY s1.trader, s2.trader
        HAVING total_value > 0
    )

    SELECT
        'node' as type,
        address,
        NULL as target_address,
        TO_NUMBER(trade_count) as trade_count,
        TO_NUMBER(total_tokens_traded) as total_tokens_traded,
        TO_NUMBER(total_usd_traded) as total_usd_traded,
        TO_NUMBER(active_days) as active_days,
        TO_NUMBER(ROUND(avg_daily_trades, 2)) as avg_daily_trades
    FROM top_traders

    UNION ALL

    SELECT
        'edge' as type,
        source as address,
        target as target_address,
        TO_NUMBER(transaction_count) as trade_count,
        TO_NUMBER(total_tokens) as total_tokens_traded,
        TO_NUMBER(total_value) as total_usd_traded,
        NULL as active_days,
        NULL as avg_daily_trades
    FROM connections
    ORDER BY type, total_usd_traded DESC;
    """
    return evm_query


def get_solana_traders_and_connections(contract_address, start_date, end_date, min_usd_amount=1, max_usd_amount=100000000, min_active_days=3, limit=200):
    """
    Get both top traders and their connections in a single query for Solana chain, excluding CEX, DEX, Pools,
    and bridge addresses, with additional trading pattern analysis.

    Parameters:
    contract_address (str): Token mint address
    start_date (str): Start date in YYYY-MM-DD format
    end_date (str): End date in YYYY-MM-DD format
    min_usd_amount (float): Minimum USD amount for trades to be considered
    max_usd_amount (float): Maximum USD amount for trades to be considered
    min_active_days (int): Minimum number of different days with trading activity
    limit (int): Number of top traders to return
    """
    print("📦 Preparing query for:")
    print(f"🪙 Contract Address: {contract_address}")
    print(f"📅 Date Range: {start_date} to {end_date}")
    print(f"💰 USD Amount Range: {min_usd_amount} to {max_usd_amount}")
    print(f"📊 Minimum Active Days: {min_active_days}")
    print(f"🏆 Top Traders Limit: {limit}")
    print("-" * 60)

    sol_query = f"""
    WITH swap_transactions AS (
    SELECT
        block_timestamp,
        swapper as trader,
        swap_from_amount as token_amount,
        COALESCE(swap_from_amount_usd, 0) + COALESCE(swap_to_amount_usd, 0) as amount_usd,
        tx_id
    FROM solana.defi.ez_dex_swaps
    WHERE (swap_from_mint = '{contract_address}' OR swap_to_mint = '{contract_address}')
        AND block_timestamp BETWEEN '{start_date}' AND '{end_date}'
        AND COALESCE(swap_from_amount_usd, 0) + COALESCE(swap_to_amount_usd, 0) >= {min_usd_amount}
        AND COALESCE(swap_from_amount_usd, 0) + COALESCE(swap_to_amount_usd, 0) <= {max_usd_amount}
    ),

    trading_patterns AS (
        SELECT
            trader,
            COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) as active_days,
            COUNT(DISTINCT tx_id) as total_trades,
            COUNT(DISTINCT tx_id) / COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) as avg_daily_trades,
            SUM(amount_usd) as total_volume
        FROM swap_transactions
        GROUP BY trader
        HAVING
            COUNT(DISTINCT DATE_TRUNC('day', block_timestamp)) >= {min_active_days}
            AND COUNT(DISTINCT tx_id) >= 5
    ),

    filtered_traders AS (
        SELECT DISTINCT
            tp.trader as address
        FROM trading_patterns tp
        WHERE tp.trader NOT IN (
            SELECT DISTINCT l.address
            FROM solana.core.dim_labels l
            WHERE label_type IN (
                'cex', 'dex', 'defi', 'bridge', 'contract', 'treasury', 'infrastructure', 'token'
            )
            OR label_subtype IN (
                'pool', 'router', 'exchange', 'mev_bot', 'flash_loan', 'vault',
                'wrapper', 'burn_address', 'null_address', 'token_account'
            )
            OR LOWER(address_name) LIKE ANY (
                '%pool%', '%bot%', '%mev%', '%vault%', '%treasury%',
                '%wrapper%', '%flash%loan%', '%token%account%', '%amm%'
            )
            LIMIT 1000
        )
    ),

    trader_nodes AS (
        SELECT
            'node' as type,
            st.trader as address,
            NULL as target_address,
            COUNT(DISTINCT st.tx_id) as trade_count,
            SUM(st.token_amount) as total_tokens_traded,
            SUM(st.amount_usd) as total_usd_traded,
            tp.active_days,
            tp.avg_daily_trades
        FROM swap_transactions st
        JOIN trading_patterns tp ON st.trader = tp.trader
        WHERE st.trader IN (SELECT address FROM filtered_traders)
        GROUP BY st.trader, tp.active_days, tp.avg_daily_trades
        ORDER BY total_usd_traded DESC
        LIMIT {limit}
    ),

    transfers_between_traders AS (
        SELECT
            'edge' as type,
            tx_from as address,
            tx_to as target_address,
            COUNT(DISTINCT tx_id) as trade_count,
            SUM(amount) as total_tokens_traded,
            SUM(amount * COALESCE(p.price, 0)) as total_usd_traded,
            NULL as active_days,
            NULL as avg_daily_trades
        FROM solana.core.fact_transfers ft
        LEFT JOIN solana.price.ez_prices_hourly p
            ON p.token_address = '{contract_address}'
            AND DATE_TRUNC('hour', ft.block_timestamp) = p.hour
        WHERE ft.block_timestamp BETWEEN '{start_date}' AND '{end_date}'
        AND ft.mint = '{contract_address}'
        AND ft.tx_from IN (SELECT address FROM trader_nodes)
        AND ft.tx_to IN (SELECT address FROM trader_nodes)
        GROUP BY tx_from, tx_to
        HAVING SUM(amount) > 0
    )

    SELECT
        type,
        address,
        target_address,
        trade_count,
        TO_NUMBER(total_tokens_traded) as total_tokens_traded,
        TO_NUMBER(total_usd_traded) as total_usd_traded,
        active_days,
        ROUND(avg_daily_trades, 2) as avg_daily_trades
    FROM trader_nodes

    UNION ALL

    SELECT
        type,
        address,
        target_address,
        trade_count,
        TO_NUMBER(total_tokens_traded) as total_tokens_traded,
        TO_NUMBER(total_usd_traded) as total_usd_traded,
        active_days,
        avg_daily_trades
    FROM transfers_between_traders
    ORDER BY type, total_usd_traded DESC;
    """
    return sol_query
