

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_products_with_recipes AS
SELECT 
    p.id,
    p.tenant_id,
    p.name,
    p.sku,
    p.category_id,
    p.sale_price,
    p.stock_quantity,
    p.is_active,
    p.needs_preparation,
    
    -- Ingredientes agregados em JSON
    COALESCE(
        json_agg(
            json_build_object(
                'ingredient_id', r.ingredient_id,
                'ingredient_name', i.name,
                'ingredient_sku', i.sku,
                'quantity', r.quantity,
                'unit', i.measure_unit,
                'current_stock', i.stock_quantity,
                'cost_per_unit', i.purchase_price
            )
            ORDER BY i.name
        ) FILTER (WHERE r.ingredient_id IS NOT NULL),
        '[]'::json
    ) as ingredients,
    
    -- Custo total da receita (soma dos ingredientes)
    COALESCE(
        SUM(r.quantity * i.purchase_price),
        0
    ) as recipe_cost,
    
    -- Margem de lucro real considerando custo da receita
    CASE 
        WHEN SUM(r.quantity * i.purchase_price) > 0 
        THEN ((p.sale_price - SUM(r.quantity * i.purchase_price)) / SUM(r.quantity * i.purchase_price) * 100)
        ELSE 0
    END as real_profit_margin,
    
    -- Verifica se todos ingredientes têm estoque suficiente
    BOOL_AND(i.stock_quantity >= r.quantity) as can_be_prepared,
    
    p.created_at,
    p.updated_at
    
FROM 
    products p
LEFT JOIN 
    recipes r ON r.product_id = p.id
LEFT JOIN 
    products i ON i.id = r.ingredient_id
WHERE
    p.needs_preparation = TRUE
GROUP BY 
    p.id;


CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_products_recipes_id ON mv_products_with_recipes(id);
CREATE INDEX IF NOT EXISTS idx_mv_products_recipes_tenant ON mv_products_with_recipes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_mv_products_recipes_active ON mv_products_with_recipes(tenant_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_mv_products_recipes_can_prepare ON mv_products_with_recipes(tenant_id, can_be_prepared) WHERE can_be_prepared = TRUE AND is_active = TRUE;

CREATE OR REPLACE FUNCTION refresh_products_recipes_mv()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_products_with_recipes;
END;
$$ LANGUAGE plpgsql;

-- 3. TRIGGERS PARA MANTER SINCRONIZADO
-- Quando produto muda
CREATE OR REPLACE FUNCTION trg_refresh_recipes_on_product_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Apenas refresh se for produto com receita
    IF (TG_OP = 'UPDATE' AND (
        NEW.needs_preparation != OLD.needs_preparation OR
        NEW.sale_price != OLD.sale_price OR
        NEW.stock_quantity != OLD.stock_quantity OR
        NEW.is_active != OLD.is_active
    )) OR TG_OP IN ('INSERT', 'DELETE') THEN
        PERFORM refresh_products_recipes_mv();
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER trg_product_refresh_recipes
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW
WHEN (pg_trigger_depth() = 0) -- Evita recursão
EXECUTE FUNCTION trg_refresh_recipes_on_product_change();

-- Quando receita muda
CREATE OR REPLACE FUNCTION trg_refresh_recipes_on_recipe_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM refresh_products_recipes_mv();
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_recipe_refresh_recipes
AFTER INSERT OR UPDATE OR DELETE ON recipes
FOR EACH ROW
WHEN (pg_trigger_depth() = 0)
EXECUTE FUNCTION trg_refresh_recipes_on_recipe_change();


-- ============================================================================
-- 4. MATERIALIZED VIEW: VENDAS COM ITENS (OUTRO CASO DE N+1)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sales_with_items AS
SELECT 
    s.id as sale_id,
    s.tenant_id,
    s.status,
    s.subtotal,
    s.total_discount,
    s.total_amount,
    s.customer_id,
    c.name as customer_name,
    c.cpf as customer_cpf,
    s.salesperson_id,
    sp.name as salesperson_name,
    
    -- Itens agregados
    json_agg(
        json_build_object(
            'item_id', si.id,
            'product_id', si.product_id,
            'product_name', p.name,
            'quantity', si.quantity,
            'unit_price', si.unit_sale_price,
            'subtotal', si.subtotal
        )
        ORDER BY si.id
    ) as items,
    
    -- Pagamentos agregados
    COALESCE(
        (SELECT json_agg(
            json_build_object(
                'method', pay.method,
                'amount', pay.total
            )
        )
        FROM sale_payments pay
        WHERE pay.sale_id = s.id),
        '[]'::json
    ) as payments,
    
    COUNT(si.id) as items_count,
    
    s.created_at,
    s.finished_at
    
FROM sales s
LEFT JOIN sale_items si ON si.sale_id = s.id
LEFT JOIN products p ON p.id = si.product_id
LEFT JOIN users c ON c.id = s.customer_id
LEFT JOIN users sp ON sp.id = s.salesperson_id
GROUP BY s.id, c.name, c.cpf, sp.name;

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_items_id ON mv_sales_with_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_mv_sales_items_tenant_status ON mv_sales_with_items(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_mv_sales_items_customer ON mv_sales_with_items(customer_id) WHERE customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_sales_items_created ON mv_sales_with_items(created_at DESC);

-- Refresh automático
CREATE OR REPLACE FUNCTION trg_refresh_sales_mv()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_with_items;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER trg_sales_refresh_mv
AFTER INSERT OR UPDATE OR DELETE ON sales
FOR EACH STATEMENT
EXECUTE FUNCTION trg_refresh_sales_mv();

CREATE OR REPLACE TRIGGER trg_sale_items_refresh_mv
AFTER INSERT OR UPDATE OR DELETE ON sale_items
FOR EACH STATEMENT
EXECUTE FUNCTION trg_refresh_sales_mv();