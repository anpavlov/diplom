function ()
    local id = tonumber(args.user_id[0])
    if id == nil then
        error("not enough data in arguments")
    end

    local status, errorString = db:execute(string.format(
                                            [[DELETE FROM m_user_User WHERE id=%d]],
                                            id))
    if status == 0 then
        return {res="error", error=errorString}
    end

    return {res="ok"}
end