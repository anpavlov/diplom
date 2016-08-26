function ()
--    local id = tonumber(args.user_id[0])
    local first_name = args.first_name[0]
    local last_name = args.last_name[0]
    local middle_name = args.middle_name[0]
    local birth_date = args.birth_date[0]
    if first_name == nil or last_name == nil or middle_name == nil or birth_date == nil then
        error("not enough data in arguments")
    end

    local status, errorString = db:execute(string.format(
                                            [[INSERT INTO m_user_User (first_name, last_name, middle_name, birth_date) VALUES (%q, %q, %q, %q)]],
                                            first_name, last_name, middle_name, birth_date))
    if status == 0 then
        return {error=errorString, res="error"}
    end
    local id = db:getlastautoid()
    local res = {}
    res.id = id
    res.first_name = first_name
    res.last_name = last_name
    res.middle_name = middle_name
    res.birth_date = birth_date

    return res
end