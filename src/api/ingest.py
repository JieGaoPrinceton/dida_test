import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.etl.cleaner import clean_email_body, strip_html
from src.etl.classifier import classify_email, extract_tags
from src.etl.importer import parse_csv, parse_json, validate_email_data
from src.etl.indexer import email_to_es_doc
from src.models.email import EmailBulkImport, EmailCreate, EmailResponse
from src.services.email_service import bulk_create_emails, create_email
from src.services.es_service import bulk_index_emails

router = APIRouter()


@router.post("/email", response_model=EmailResponse, status_code=201)
async def ingest_single(email_data: EmailCreate, db: AsyncSession = Depends(get_db)):
    if email_data.body_html and not email_data.body_text:
        email_data.body_text = strip_html(email_data.body_html)
    email_data.body_text = clean_email_body(email_data.body_text)

    if not email_data.category:
        cat, subcat = classify_email(email_data.subject, email_data.body_text)
        email_data.category = cat
        email_data.subcategory = subcat

    if not email_data.tags:
        email_data.tags = extract_tags(email_data.subject, email_data.body_text)

    email = await create_email(db, email_data)
    doc = email_to_es_doc(email)
    await bulk_index_emails([doc])
    return email


@router.post("/emails", status_code=201)
async def ingest_bulk(payload: EmailBulkImport, db: AsyncSession = Depends(get_db)):
    for em in payload.emails:
        if em.body_html and not em.body_text:
            em.body_text = strip_html(em.body_html)
        em.body_text = clean_email_body(em.body_text)
        if not em.category:
            cat, subcat = classify_email(em.subject, em.body_text)
            em.category = cat
            em.subcategory = subcat
        if not em.tags:
            em.tags = extract_tags(em.subject, em.body_text)

    ids = await bulk_create_emails(db, payload.emails)
    return {"imported": len(ids), "ids": ids}


@router.post("/upload/csv", status_code=201)
async def upload_csv(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = await file.read()
    rows = parse_csv(content)
    emails = []
    errors = []
    for i, row in enumerate(rows):
        try:
            em = validate_email_data(row)
            em.body_text = clean_email_body(em.body_text)
            if not em.category:
                cat, subcat = classify_email(em.subject, em.body_text)
                em.category = cat
                em.subcategory = subcat
            if not em.tags:
                em.tags = extract_tags(em.subject, em.body_text)
            emails.append(em)
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    if not emails:
        raise HTTPException(status_code=400, detail="No valid emails found in CSV")

    ids = await bulk_create_emails(db, emails)
    return {"imported": len(ids), "errors": len(errors), "error_details": errors[:20]}


@router.post("/upload/json", status_code=201)
async def upload_json(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be JSON")
    content = await file.read()
    rows = parse_json(content)
    emails = []
    errors = []
    for i, row in enumerate(rows):
        try:
            em = validate_email_data(row)
            em.body_text = clean_email_body(em.body_text)
            if not em.category:
                cat, subcat = classify_email(em.subject, em.body_text)
                em.category = cat
                em.subcategory = subcat
            if not em.tags:
                em.tags = extract_tags(em.subject, em.body_text)
            emails.append(em)
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    if not emails:
        raise HTTPException(status_code=400, detail="No valid emails found in JSON")

    ids = await bulk_create_emails(db, emails)
    return {"imported": len(ids), "errors": len(errors), "error_details": errors[:20]}
