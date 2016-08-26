function ()
    local cursor, errorString = db:execute([[SELECT id, first_name, last_name, middle_name, birth_date FROM m_user_User]])
    if cursor == nil then
        return {error=errorString, er2="cursor is nil"}
    end
    local row = cursor:fetch({}, 'a')
    if row == nil then
        return {error='empty result'}
    end
    local res = {}
    res.users = {}
    local n = 0
    while row do
        n = n + 1
        local t = {}
        t.id = row.id
        t.middle_name = row.middle_name
        t.first_name = row.first_name
        t.last_name = row.last_name
        t.birth_date = row.birth_date
        res.users[n] = t
        row = cursor:fetch({}, 'a')
    end

        return res
end