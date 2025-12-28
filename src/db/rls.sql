-- ============================================================================
-- RLS (ROW LEVEL SECURITY) - SCMG
-- ============================================================================

-- ============================================================================
-- FUNÇÕES AUXILIARES PARA RLS
-- ============================================================================

-- Retorna o user_id da sessão atual
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS UUID SET search_path = public, extensions, pg_temp AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;


-- Retorna o tenant_id da sessão atual
CREATE OR REPLACE FUNCTION current_user_tenant_id()
RETURNS UUID SET search_path = public, extensions, pg_temp AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_tenant_id', TRUE), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;


-- Retorna as roles do usuário atual
CREATE OR REPLACE FUNCTION current_user_roles()
RETURNS user_role_enum[] SET search_path = public, extensions, pg_temp AS $$
BEGIN
    RETURN COALESCE(
        NULLIF(current_setting('app.current_user_roles', TRUE), '')::user_role_enum[],
        ARRAY[]::user_role_enum[]
    );
EXCEPTION
    WHEN OTHERS THEN RETURN ARRAY[]::user_role_enum[];
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;


-- Retorna o nível máximo de privilégio do usuário atual
CREATE OR REPLACE FUNCTION current_user_max_privilege()
RETURNS INTEGER SET search_path = public, extensions, pg_temp AS $$
BEGIN    
    RETURN COALESCE(
        NULLIF(current_setting('app.current_user_max_privilege', TRUE), '')::INTEGER,
        0
    );
EXCEPTION
    WHEN OTHERS THEN RETURN 0;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION debug_session_context()
RETURNS JSONB 
SET search_path = public, extensions, pg_temp
AS $$
BEGIN
    RETURN jsonb_build_object(
        'user_id', current_user_id(),
        'tenant_id', current_user_tenant_id(),
        'roles', current_user_roles(),
        'max_privilege', current_user_max_privilege()
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- ============================================================================
-- ROLE CONFIGS
-- ============================================================================

ALTER TABLE role_configs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS role_configs_read_policy ON role_configs;
CREATE POLICY role_configs_read_policy ON role_configs 
    FOR SELECT 
    USING (true);

-- ============================================================================
-- IBPT VERSIONS
-- ============================================================================

ALTER TABLE ibpt_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ibpt_versions_read_policy ON ibpt_versions;
CREATE POLICY ibpt_versions_read_policy ON ibpt_versions 
    FOR SELECT 
    USING (true);

-- ============================================================================
-- FISCAL NCMS
-- ============================================================================

ALTER TABLE fiscal_ncms ENABLE ROW LEVEL SECURITY;

-- [SELECT]: Leitura pública
DROP POLICY IF EXISTS fiscal_ncms_public_read ON fiscal_ncms;
CREATE POLICY fiscal_ncms_public_read ON fiscal_ncms
    FOR SELECT
    USING (true);

-- ============================================================================
-- TENANTS
-- ============================================================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenants_select_policy ON tenants;
CREATE POLICY tenants_select_policy ON tenants
    FOR SELECT
    USING (id = current_user_tenant_id());


-- ============================================================================
-- USERS
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_tenant_isolation ON users;
CREATE POLICY users_tenant_isolation ON users
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());


-- ============================================================================
-- CATEGORIES
-- ============================================================================

ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS categories_tenant_isolation ON categories;
CREATE POLICY categories_tenant_isolation ON categories
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());


-- ============================================================================
-- SUPPLIERS
-- ============================================================================

ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS suppliers_tenant_isolation ON suppliers;
CREATE POLICY suppliers_tenant_isolation ON suppliers
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- TAX_GROUPS
-- ============================================================================

ALTER TABLE tax_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tax_groups_tenant_isolation ON tax_groups;
CREATE POLICY tax_groups_tenant_isolation ON tax_groups
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- PRODUCTS
-- ============================================================================

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS products_tenant_isolation ON products;
CREATE POLICY products_tenant_isolation ON products
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- PRODUCT_COMPOSITIONS
-- ============================================================================

ALTER TABLE product_compositions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_compositions_tenant_isolation ON product_compositions;
CREATE POLICY product_compositions_tenant_isolation ON product_compositions
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());


-- ============================================================================
-- PRODUCT_MODIFIER_GROUPS
-- ============================================================================

ALTER TABLE product_modifier_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_modifier_groups_tenant_isolation ON product_modifier_groups;
CREATE POLICY product_modifier_groups_tenant_isolation ON product_modifier_groups
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- BATCHES
-- ============================================================================

ALTER TABLE batches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS batches_tenant_isolation ON batches;
CREATE POLICY batches_tenant_isolation ON batches
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- ADDRESSES
-- ============================================================================
ALTER TABLE addresses ENABLE ROW LEVEL SECURITY;

-- Tabela compartilhada (cache de CEPs)
DROP POLICY IF EXISTS addresses_public_read ON addresses;
CREATE POLICY addresses_public_read ON addresses
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS addresses_public_write ON addresses;
CREATE POLICY addresses_public_write ON addresses
    FOR INSERT
    WITH CHECK (true);

DROP POLICY IF EXISTS addresses_public_update ON addresses;
CREATE POLICY addresses_public_update ON addresses
    FOR UPDATE
    USING (true);


-- ============================================================================
-- USER_ADDRESSES
-- ============================================================================

ALTER TABLE user_addresses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_addresses_tenant_isolation ON user_addresses;
CREATE POLICY user_addresses_tenant_isolation ON user_addresses
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- REFRESH_TOKENS
-- ============================================================================

ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;

-- [SELECT] Usuário vê os próprios tokens
DROP POLICY IF EXISTS refresh_tokens_own_access ON refresh_tokens;
CREATE POLICY refresh_tokens_own_access ON refresh_tokens
    FOR ALL
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());


-- ============================================================================
-- PRICE_AUDITS
-- ============================================================================

ALTER TABLE price_audits ENABLE ROW LEVEL SECURITY;

-- Apenas leitura, todos veem do seu tenant
DROP POLICY IF EXISTS price_audits_select_policy ON price_audits;
CREATE POLICY price_audits_select_policy ON price_audits
    FOR SELECT
    USING (tenant_id = current_user_tenant_id());

-- ============================================================================
-- STOCK_MOVEMENTS
-- ============================================================================

ALTER TABLE stock_movements ENABLE ROW LEVEL SECURITY;


DROP POLICY IF EXISTS stock_movements_select_policy ON stock_movements;
CREATE POLICY stock_movements_select_policy ON stock_movements
    FOR SELECT
    USING (
        tenant_id = current_user_tenant_id()
        AND current_user_max_privilege() > 0
    );


DROP POLICY IF EXISTS stock_movements_insert_policy ON stock_movements;
CREATE POLICY stock_movements_insert_policy ON stock_movements
    FOR INSERT
    WITH CHECK (
        tenant_id = current_user_tenant_id()
        AND current_user_max_privilege() > 0
    );


DROP POLICY IF EXISTS stock_movements_update_policy ON stock_movements;
CREATE POLICY stock_movements_update_policy ON stock_movements
    FOR UPDATE
    USING (false) -- Sempre Falso = Ninguém passa
    WITH CHECK (false);


DROP POLICY IF EXISTS stock_movements_delete_policy ON stock_movements;
CREATE POLICY stock_movements_delete_policy ON stock_movements
    FOR DELETE
    USING (false); -- Sempre Falso


-- ============================================================================
-- FISCAL SEQUENCES
-- ============================================================================
-- RLS para Segurança (Ninguém vê a sequência do vizinho)
ALTER TABLE fiscal_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiscal_sequences FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS fiscal_sequences_isolation ON fiscal_sequences;
CREATE POLICY fiscal_sequences_isolation ON fiscal_sequences
    FOR ALL
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- SALES
-- ============================================================================

ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sales_isolation ON sales;
CREATE POLICY sales_isolation ON sales
    FOR ALL
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- SALE_ITEMS
-- ============================================================================

ALTER TABLE sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_items FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sale_items_isolation ON sale_items;
CREATE POLICY sale_items_isolation ON sale_items
    FOR ALL
    USING (true);


-- ============================================================================
-- APP TOKENS
-- ============================================================================

ALTER TABLE app_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_tokens FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_tokens_public_all ON app_tokens;
CREATE POLICY app_tokens_public_all ON app_tokens
    FOR ALL
    USING (true)
    WITH CHECK (true);


-- ============================================================================
-- SALE_PAYMENTS
-- ============================================================================

ALTER TABLE sale_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_payments FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sale_payments_isolation ON sale_payments;
CREATE POLICY sale_payments_isolation ON sale_payments
    FOR ALL
    USING (true);

-- ============================================================================
-- LOGS
-- ============================================================================

ALTER TABLE logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS logs_admin_only ON logs;
CREATE POLICY logs_admin_only ON logs
    FOR SELECT
    USING ('ADMIN' = ANY(current_user_roles()));


DROP POLICY IF EXISTS logs_insert_policy ON logs;
CREATE POLICY logs_insert_policy ON logs
    FOR INSERT
    WITH CHECK (true);

-- ============================================================================
-- USER_FEEDBACKS
-- ============================================================================

ALTER TABLE user_feedbacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedbacks FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS feedbacks_own_access ON user_feedbacks;
CREATE POLICY feedbacks_own_access ON user_feedbacks
    FOR ALL
    USING (
        user_id = current_user_id() 
        OR 'ADMIN' = ANY(current_user_roles())
    );

-- ============================================================================
-- SECURITY_AUDIT_LOG
-- ============================================================================

ALTER TABLE security_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS security_audit_log_isolation ON security_audit_log;
CREATE POLICY security_audit_log_isolation ON security_audit_log
    FOR ALL
    USING (tenant_id = current_user_tenant_id())
    WITH CHECK (tenant_id = current_user_tenant_id());

-- ============================================================================
-- FISCAL PAYMENT CODES
-- ============================================================================

ALTER TABLE fiscal_payment_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE fiscal_payment_codes FORCE ROW LEVEL SECURITY;

-- [SELECT] Leitura pública
DROP POLICY IF EXISTS fiscal_payment_codes_public_read ON fiscal_payment_codes;
CREATE POLICY fiscal_payment_codes_public_read ON fiscal_payment_codes
    FOR SELECT
    USING (true);


-- ============================================================================
-- CNPJS
-- ============================================================================

ALTER TABLE cnpjs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cnpjs FORCE ROW LEVEL SECURITY;

-- [SELECT]
DROP POLICY IF EXISTS cnpjs_public_all ON cnpjs;
CREATE POLICY cnpjs_public_all ON cnpjs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- CURRENCIES
-- ============================================================================

ALTER TABLE currencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE currencies FORCE ROW LEVEL SECURITY;

-- [SELECT]: Leitura pública
DROP POLICY IF EXISTS currencies_public_read ON currencies;
CREATE POLICY currencies_public_read ON currencies
    FOR SELECT
    USING (true);

