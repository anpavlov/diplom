function ()
    local str_id = args.user_id[0]
    if str_id == nil then
        error("no id in arguments")
    end
    local id = tonumber(str_id)
    local first_name = args.first_name[0]
    local last_name = args.last_name[0]
    local middle_name = args.middle_name[0]
    local birth_date = args.birth_date[0]
    if id == nil or first_name == nil or last_name == nil or middle_name == nil or birth_date == nil then
        error("not enough data in arguments")
    end

    local status, errorString = db:execute(string.format(
                                            [[UPDATE m_user_User SET first_name=%q, last_name=%q, middle_name=%q, birth_date=%q WHERE id=%d]],
                                            first_name, last_name, middle_name, birth_date, id))
    if status == 0 then
        return {res="error", error=errorString}
    end

    return {res="ok"}
end