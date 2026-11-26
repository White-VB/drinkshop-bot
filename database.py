import os, asyncpg
_pool=None
async def init_db(products):
    global _pool
    _pool=await asyncpg.create_pool(os.environ["DATABASE_URL"])
    async with _pool.acquire() as c:
        await c.execute("""CREATE TABLE IF NOT EXISTS products(
          id SERIAL PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,price NUMERIC NOT NULL,
          quantity INTEGER NOT NULL DEFAULT 0,photo TEXT,award TEXT,category TEXT NOT NULL,subcategory TEXT)""")
        await c.execute("""CREATE TABLE IF NOT EXISTS orders(
          id BIGSERIAL PRIMARY KEY,user_id BIGINT,username TEXT,details TEXT,items TEXT,total NUMERIC,
          created_at TIMESTAMPTZ DEFAULT NOW())""")
        count=await c.fetchval("SELECT COUNT(*) FROM products")
        if count==0:
            for p in products:
                await c.execute("""INSERT INTO products(name,description,price,quantity,photo,award,category,subcategory)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8)""",*p)
async def list_products(cat,sub=None):
    async with _pool.acquire() as c:
        if sub: rows=await c.fetch("SELECT id,name,description,price,quantity,photo,award,category,subcategory FROM products WHERE category=$1 AND subcategory=$2 AND quantity>0 ORDER BY name",cat,sub)
        else: rows=await c.fetch("SELECT id,name,description,price,quantity,photo,award,category,subcategory FROM products WHERE category=$1 AND quantity>0 ORDER BY name",cat)
    return [tuple(r) for r in rows]
async def get_product(pid):
    async with _pool.acquire() as c:
        r=await c.fetchrow("SELECT id,name,description,price,quantity,photo,award,category,subcategory FROM products WHERE id=$1",pid)
    return tuple(r) if r else None
async def create_order(uid,username,details,items,total):
    async with _pool.acquire() as c:
        return await c.fetchval("INSERT INTO orders(user_id,username,details,items,total) VALUES($1,$2,$3,$4,$5) RETURNING id",uid,username,details,"\n".join(items),total)
async def set_stock(pid,qty):
    async with _pool.acquire() as c: await c.execute("UPDATE products SET quantity=$2 WHERE id=$1",pid,qty)
async def set_price(pid,price):
    async with _pool.acquire() as c: await c.execute("UPDATE products SET price=$2 WHERE id=$1",pid,price)
