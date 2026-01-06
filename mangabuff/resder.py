def process_single_batch(session: requests.Session, base_url: str, chapters_batch: list[dict[str, Any]]) -> Dict[str, int]:
    """
    Обробляє одну порцію глав: відправляє історію.
    Перевіряє відповідь на наявність цукерки (і забирає її) або картки.
    
    Повертає словник: {'candies': int, 'cards': int}
    """
    url = f"{base_url}{ADD_HISTORY_PATH}"
    
    payload: dict[str, Any] = {}
    for i, item in enumerate(chapters_batch):
        for key, value in item.items():
            payload[f"items[{i}][{key}]"] = value
    
    history_response = make_request(
        session, 
        'POST', 
        url, 
        delay=180.0,
        data=payload, 
        headers_profile="ajax_post"
    )
    
    result = {'candies': 0, 'cards': 0}

    if not history_response or not isinstance(history_response, dict):
        logging.error("Не отримано валідної відповіді від сервера /addHistory.")
        return result

    # 1. Перевірка на ЦУКЕРКУ
    candy_token = history_response.get("token")
    if candy_token:
        take_candy(session, base_url, candy_token)
        
        candy_type = history_response.get("type")
        
        if candy_type == "pumpkin":
            result['candies'] = 3 
            logging.info(f"✅ УСПІХ! Знайдено гарбуз! +{result['candies']} до прогресу.")
        else:
            result['candies'] = 1
            logging.info(f"✅ УСПІХ! Взято нову цукерку. +{result['candies']} до прогресу.")
            
        return result

    # 2. Перевірка на КАРТКУ
    # Формат: {'id': 191889, 'name': 'Уин', 'image': '/img/cards/...'}
    if 'id' in history_response and 'name' in history_response and 'image' in history_response:
        card_name = history_response.get('name')
        logging.info(f"🃏 ЗНАЙДЕНО КАРТКУ: '{card_name}'! (ID: {history_response.get('id')})")
        
        # Картку "збирати" окремим запитом не потрібно, вона вже зарахована фактом випадіння
        result['cards'] = 1
        return result

    # 3. Нічого не знайдено
    logging.info(f"Ресурсів не знайдено у відповіді (Token/Card відсутні).")
    return result
