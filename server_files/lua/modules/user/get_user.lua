function ()
    local id = tonumber(args.user_id[0])
    if id == nil then
        error("no user_id in arguments")
    end

    local cursor, errorString = db:execute(string.format([[SELECT first_name, last_name, middle_name, birth_date FROM m_user_User WHERE id=%d]], id))
    if cursor == nil then
        return {error=errorString, er2="cursor is nil"}
    end
    local row = cursor:fetch({}, 'a')
    if row == nil then
        return {error='empty result'}
    end
    local res = {}
    res.id = id
    res.first_name = row.first_name
    res.last_name = row.last_name
    res.middle_name = row.middle_name
    res.birth_date = row.birth_date

    return res
end