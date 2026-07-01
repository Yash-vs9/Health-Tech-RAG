-- ════════════════════════════════════════════════════════════════════════
-- Mortgage RAG — Auth & Session Schema
-- Run this in Supabase SQL Editor (Project → SQL Editor → New Query)
-- ════════════════════════════════════════════════════════════════════════

-- 1. USER PROFILES
create table if not exists public.profiles (
    id          uuid primary key references auth.users(id) on delete cascade,
    email       text not null,
    full_name   text,
    avatar_url  text,
    provider    text default 'email',
    created_at  timestamptz default now(),
    updated_at  timestamptz default now()
);

create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.profiles (id, email, full_name, avatar_url, provider)
    values (
        new.id,
        new.email,
        new.raw_user_meta_data ->> 'full_name',
        new.raw_user_meta_data ->> 'avatar_url',
        coalesce(new.raw_app_meta_data ->> 'provider', 'email')
    )
    on conflict (id) do nothing;
    return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();


-- 2. CHAT SESSIONS
create table if not exists public.chat_sessions (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles(id) on delete cascade,
    title       text not null default 'New Chat',
    created_at  timestamptz default now(),
    updated_at  timestamptz default now()
);

create index if not exists idx_chat_sessions_user on public.chat_sessions(user_id);


-- 3. DOCUMENTS
create table if not exists public.documents (
    id              uuid primary key default gen_random_uuid(),
    chat_session_id uuid not null references public.chat_sessions(id) on delete cascade,
    user_id         uuid not null references public.profiles(id) on delete cascade,
    filename        text not null,
    storage_path    text not null,
    file_size_bytes bigint,
    doc_id          text not null,
    num_chunks      integer default 0,
    status          text default 'processing',
    uploaded_at     timestamptz default now()
);

create index if not exists idx_documents_chat_session on public.documents(chat_session_id);
create index if not exists idx_documents_user on public.documents(user_id);


-- 4. MESSAGES
create table if not exists public.messages (
    id              uuid primary key default gen_random_uuid(),
    chat_session_id uuid not null references public.chat_sessions(id) on delete cascade,
    role            text not null,
    content         text not null,
    sources         jsonb,
    created_at      timestamptz default now()
);

create index if not exists idx_messages_chat_session on public.messages(chat_session_id, created_at);


-- 5. ROW LEVEL SECURITY
alter table public.profiles      enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.documents     enable row level security;
alter table public.messages      enable row level security;

create policy "profiles_select_own" on public.profiles
    for select using (auth.uid() = id);
create policy "profiles_update_own" on public.profiles
    for update using (auth.uid() = id);

create policy "chat_sessions_all_own" on public.chat_sessions
    for all using (auth.uid() = user_id);

create policy "documents_all_own" on public.documents
    for all using (auth.uid() = user_id);

create policy "messages_select_own" on public.messages
    for select using (
        exists (
            select 1 from public.chat_sessions cs
            where cs.id = messages.chat_session_id
            and cs.user_id = auth.uid()
        )
    );
create policy "messages_insert_own" on public.messages
    for insert with check (
        exists (
            select 1 from public.chat_sessions cs
            where cs.id = messages.chat_session_id
            and cs.user_id = auth.uid()
        )
    );


-- 6. AUTO-UPDATE updated_at ON CHAT SESSIONS
create or replace function public.touch_chat_session()
returns trigger as $$
begin
    update public.chat_sessions
    set updated_at = now()
    where id = new.chat_session_id;
    return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_message_inserted on public.messages;
create trigger on_message_inserted
    after insert on public.messages
    for each row execute procedure public.touch_chat_session();


-- 7. STORAGE BUCKET
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

create policy "storage_select_own"
    on storage.objects for select
    using (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "storage_insert_own"
    on storage.objects for insert
    with check (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "storage_delete_own"
    on storage.objects for delete
    using (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);
